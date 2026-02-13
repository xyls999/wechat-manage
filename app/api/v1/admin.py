from datetime import datetime, timedelta
import json
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import and_, delete, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_password_hash, verify_token
from app.models.admin_audit_log import AdminAuditLog
from app.models.file import File as FileModel, FileStatus, FileType
from app.models.user import User
from app.schemas.admin import (
    AdminFileBatchDeleteRequest,
    AdminFileItem,
    AdminFileListResponse,
    AdminFileUpdate,
    AdminStatsResponse,
    AdminUserCreate,
    AdminUserDetailResponse,
    AdminUserItem,
    AdminUserListResponse,
    AdminUserUpdate,
    CleanupConfigResponse,
    CleanupRunResponse,
)
from app.schemas.response import ApiResponse
from app.services.cleanup import cleanup_expired_files

router = APIRouter()
optional_security = HTTPBearer(auto_error=False)


def _enforce_origin(request: Request) -> None:
    allowed_origins = settings.ADMIN_ALLOWED_ORIGINS
    if "*" in allowed_origins:
        return

    origin = request.headers.get("origin")
    if not origin:
        return
    if origin not in allowed_origins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="来源不被允许")


async def _get_admin_actor(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: AsyncSession = Depends(get_db),
) -> str:
    _enforce_origin(request)

    if not settings.ADMIN_AUTH_ENABLED:
        return "system"

    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少认证凭据")

    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效认证凭据")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active or not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无管理员权限")

    return user.username


async def _write_audit_log(
    db: AsyncSession,
    actor: str,
    action: str,
    target_type: str,
    target_id: str,
    details: Optional[dict] = None,
) -> None:
    log = AdminAuditLog(
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=json.dumps(details, ensure_ascii=False) if details else None,
    )
    db.add(log)
    await db.flush()


def _to_admin_user_item(user: User) -> AdminUserItem:
    return AdminUserItem(
        id=user.id,
        username=user.username,
        nickname=user.nickname,
        avatar=user.avatar,
        isActive=user.is_active,
        isAdmin=user.is_admin,
        createdAt=user.created_at,
        lastLoginAt=user.last_login_at,
    )


def _to_admin_file_item(file_record: FileModel, username: Optional[str]) -> AdminFileItem:
    return AdminFileItem(
        id=file_record.id,
        userId=file_record.user_id,
        username=username,
        fileName=file_record.file_name,
        fileType=file_record.file_type,
        filePath=file_record.file_path,
        fileSize=file_record.file_size,
        status=file_record.status,
        uploadTime=file_record.upload_time,
        processTime=file_record.process_time,
        remark=file_record.remark or "",
    )


@router.get("/users", response_model=ApiResponse)
async def list_users(
    keyword: Optional[str] = Query(default=None),
    isActive: Optional[bool] = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    _: str = Depends(_get_admin_actor),
    db: AsyncSession = Depends(get_db),
):
    conditions = []
    if keyword:
        like = f"%{keyword}%"
        conditions.append(or_(User.username.like(like), User.nickname.like(like)))
    if isActive is not None:
        conditions.append(User.is_active == isActive)

    count_stmt = select(func.count()).select_from(User)
    data_stmt = select(User)
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
        data_stmt = data_stmt.where(and_(*conditions))

    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(
            data_stmt.order_by(desc(User.created_at)).offset((page - 1) * pageSize).limit(pageSize)
        )
    ).scalars().all()

    response_data = AdminUserListResponse(
        list=[_to_admin_user_item(u) for u in rows],
        total=total,
        page=page,
        pageSize=pageSize,
    )
    return ApiResponse(code=200, data=response_data.model_dump())


@router.post("/users", response_model=ApiResponse)
async def create_user(
    payload: AdminUserCreate,
    actor: str = Depends(_get_admin_actor),
    db: AsyncSession = Depends(get_db),
):
    exists = (
        await db.execute(select(User).where(User.username == payload.username))
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")

    user = User(
        username=payload.username,
        password=get_password_hash(payload.password),
        nickname=payload.nickname,
        avatar="",
        is_active=payload.is_active,
        is_admin=payload.is_admin,
    )
    db.add(user)
    await db.flush()
    await _write_audit_log(
        db,
        actor=actor,
        action="create_user",
        target_type="user",
        target_id=user.id,
        details={"username": user.username},
    )
    await db.commit()
    await db.refresh(user)

    return ApiResponse(code=200, message="创建用户成功", data=_to_admin_user_item(user).model_dump())


@router.get("/users/{user_id}", response_model=ApiResponse)
async def get_user_detail(
    user_id: str,
    _: str = Depends(_get_admin_actor),
    db: AsyncSession = Depends(get_db),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    file_stats = await db.execute(
        select(func.count(FileModel.id), func.coalesce(func.sum(FileModel.file_size), 0)).where(
            FileModel.user_id == user_id
        )
    )
    file_count, total_size = file_stats.one()
    response_data = AdminUserDetailResponse(
        user=_to_admin_user_item(user),
        fileCount=file_count,
        totalFileSize=total_size,
    )
    return ApiResponse(code=200, data=response_data.model_dump())


@router.patch("/users/{user_id}", response_model=ApiResponse)
async def update_user(
    user_id: str,
    payload: AdminUserUpdate,
    actor: str = Depends(_get_admin_actor),
    db: AsyncSession = Depends(get_db),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if payload.nickname is not None:
        user.nickname = payload.nickname
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.is_admin is not None:
        user.is_admin = payload.is_admin
    if payload.reset_password:
        user.password = get_password_hash(payload.reset_password)

    await _write_audit_log(
        db,
        actor=actor,
        action="update_user",
        target_type="user",
        target_id=user_id,
        details=payload.model_dump(exclude_none=True, exclude={"reset_password"}),
    )
    await db.commit()
    await db.refresh(user)

    return ApiResponse(code=200, message="更新用户成功", data=_to_admin_user_item(user).model_dump())


@router.delete("/users/{user_id}", response_model=ApiResponse)
async def delete_user(
    user_id: str,
    actor: str = Depends(_get_admin_actor),
    db: AsyncSession = Depends(get_db),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    user_files = (
        await db.execute(select(FileModel).where(FileModel.user_id == user_id))
    ).scalars().all()
    deleted_physical = 0
    for item in user_files:
        if item.file_path and os.path.exists(item.file_path):
            try:
                os.remove(item.file_path)
                deleted_physical += 1
            except Exception:
                pass

    await db.execute(delete(FileModel).where(FileModel.user_id == user_id))
    await db.delete(user)
    await _write_audit_log(
        db,
        actor=actor,
        action="delete_user",
        target_type="user",
        target_id=user_id,
        details={"deletedFiles": len(user_files), "deletedPhysicalFiles": deleted_physical},
    )
    await db.commit()
    return ApiResponse(code=200, message="删除用户成功")


@router.get("/files", response_model=ApiResponse)
async def list_files(
    userId: Optional[str] = Query(default=None),
    fileType: Optional[FileType] = Query(default=None),
    statusFilter: Optional[FileStatus] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    dateFrom: Optional[datetime] = Query(default=None),
    dateTo: Optional[datetime] = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    _: str = Depends(_get_admin_actor),
    db: AsyncSession = Depends(get_db),
):
    conditions = []
    if userId:
        conditions.append(FileModel.user_id == userId)
    if fileType:
        conditions.append(FileModel.file_type == fileType)
    if statusFilter:
        conditions.append(FileModel.status == statusFilter)
    if keyword:
        conditions.append(FileModel.file_name.like(f"%{keyword}%"))
    if dateFrom:
        conditions.append(FileModel.upload_time >= dateFrom)
    if dateTo:
        conditions.append(FileModel.upload_time <= dateTo)

    count_stmt = select(func.count()).select_from(FileModel)
    data_stmt = select(FileModel, User.username).join(User, User.id == FileModel.user_id, isouter=True)
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
        data_stmt = data_stmt.where(and_(*conditions))

    total = (await db.execute(count_stmt)).scalar_one()
    rows = await db.execute(
        data_stmt.order_by(desc(FileModel.upload_time)).offset((page - 1) * pageSize).limit(pageSize)
    )

    items = [_to_admin_file_item(file_record, username) for file_record, username in rows.all()]
    response_data = AdminFileListResponse(list=items, total=total, page=page, pageSize=pageSize)
    return ApiResponse(code=200, data=response_data.model_dump())


@router.post("/files/batch-delete", response_model=ApiResponse)
async def batch_delete_files(
    payload: AdminFileBatchDeleteRequest,
    actor: str = Depends(_get_admin_actor),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(select(FileModel).where(FileModel.id.in_(payload.fileIds)))
    ).scalars().all()
    if not rows:
        return ApiResponse(code=200, message="没有可删除文件", data={"deleted": 0})

    deleted = 0
    for item in rows:
        if item.file_path and os.path.exists(item.file_path):
            try:
                os.remove(item.file_path)
            except Exception:
                pass
        await db.delete(item)
        deleted += 1

    await _write_audit_log(
        db,
        actor=actor,
        action="batch_delete_files",
        target_type="file",
        target_id="multiple",
        details={"deleted": deleted},
    )
    await db.commit()
    return ApiResponse(code=200, message="批量删除成功", data={"deleted": deleted})


@router.get("/files/{file_id}", response_model=ApiResponse)
async def get_file_detail(
    file_id: str,
    _: str = Depends(_get_admin_actor),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        select(FileModel, User.username).join(User, User.id == FileModel.user_id, isouter=True).where(
            FileModel.id == file_id
        )
    )
    result = row.one_or_none()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")
    file_record, username = result
    return ApiResponse(code=200, data=_to_admin_file_item(file_record, username).model_dump())


@router.patch("/files/{file_id}", response_model=ApiResponse)
async def update_file(
    file_id: str,
    payload: AdminFileUpdate,
    actor: str = Depends(_get_admin_actor),
    db: AsyncSession = Depends(get_db),
):
    file_record = (await db.execute(select(FileModel).where(FileModel.id == file_id))).scalar_one_or_none()
    if not file_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    if payload.remark is not None:
        file_record.remark = payload.remark
    if payload.status is not None:
        file_record.status = payload.status

    await _write_audit_log(
        db,
        actor=actor,
        action="update_file",
        target_type="file",
        target_id=file_id,
        details=payload.model_dump(exclude_none=True),
    )
    await db.commit()
    return ApiResponse(code=200, message="更新文件成功")


@router.delete("/files/{file_id}", response_model=ApiResponse)
async def delete_file(
    file_id: str,
    actor: str = Depends(_get_admin_actor),
    db: AsyncSession = Depends(get_db),
):
    file_record = (await db.execute(select(FileModel).where(FileModel.id == file_id))).scalar_one_or_none()
    if not file_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    if file_record.file_path and os.path.exists(file_record.file_path):
        try:
            os.remove(file_record.file_path)
        except Exception:
            pass
    await db.delete(file_record)
    await _write_audit_log(
        db,
        actor=actor,
        action="delete_file",
        target_type="file",
        target_id=file_id,
    )
    await db.commit()
    return ApiResponse(code=200, message="删除文件成功")


@router.get("/stats", response_model=ApiResponse)
async def get_stats(
    _: str = Depends(_get_admin_actor),
    db: AsyncSession = Depends(get_db),
):
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    total_files = (await db.execute(select(func.count()).select_from(FileModel))).scalar_one()
    total_storage = (
        await db.execute(select(func.coalesce(func.sum(FileModel.file_size), 0)))
    ).scalar_one()
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    uploads_last_7_days = (
        await db.execute(select(func.count()).select_from(FileModel).where(FileModel.upload_time >= seven_days_ago))
    ).scalar_one()

    data = AdminStatsResponse(
        totalUsers=total_users,
        totalFiles=total_files,
        totalStorageBytes=total_storage,
        uploadsLast7Days=uploads_last_7_days,
    )
    return ApiResponse(code=200, data=data.model_dump())


@router.get("/cleanup/config", response_model=ApiResponse)
async def get_cleanup_config(_: str = Depends(_get_admin_actor)):
    data = CleanupConfigResponse(
        retentionDays=settings.CLEANUP_RETENTION_DAYS,
        scheduleHour=settings.CLEANUP_SCHEDULE_HOUR,
        scheduleMinute=settings.CLEANUP_SCHEDULE_MINUTE,
    )
    return ApiResponse(code=200, data=data.model_dump())


@router.post("/cleanup/run", response_model=ApiResponse)
async def run_cleanup(
    actor: str = Depends(_get_admin_actor),
    db: AsyncSession = Depends(get_db),
):
    result = await cleanup_expired_files(db, settings.CLEANUP_RETENTION_DAYS)
    await _write_audit_log(
        db,
        actor=actor,
        action="run_cleanup",
        target_type="system",
        target_id="cleanup",
        details=result,
    )
    await db.commit()
    response = CleanupRunResponse(**result)
    return ApiResponse(code=200, message="清理任务执行完成", data=response.model_dump())
