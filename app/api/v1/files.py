from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, desc
from typing import Optional
import os
import uuid
from datetime import datetime
import aiofiles

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.file import File as FileModel, FileType, FileStatus
from app.schemas.file import (
    FileUploadResponse,
    FileProcessRequest,
    FileProcessResponse,
    FileDownloadResponse,
    FilePreviewResponse,
    FileHistoryResponse,
    FileHistoryItem
)
from app.schemas.response import ApiResponse
from app.services.excel_processor import ExcelProcessor

router = APIRouter()

ALLOWED_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/octet-stream",
}


def _infer_excel_extension(filename: str, content_type: str, content: bytes) -> str:
    lower_name = (filename or "").lower()
    if lower_name.endswith(".xlsx"):
        return ".xlsx"
    if lower_name.endswith(".xls"):
        return ".xls"

    lower_type = (content_type or "").lower()
    if lower_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        return ".xlsx"
    if lower_type == "application/vnd.ms-excel":
        return ".xls"

    # xlsx zip magic: PK
    if len(content) >= 2 and content[:2] == b"PK":
        return ".xlsx"
    # xls ole2 magic
    if len(content) >= 8 and content[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return ".xls"
    return ""

@router.post("/upload", response_model=ApiResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """上传Excel文件"""
    # 读取文件内容
    content = await file.read()
    file_size = len(content)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件内容为空"
        )
    
    # 检查文件大小
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制({settings.MAX_FILE_SIZE / 1024 / 1024}MB)"
        )
    
    # 检查文件类型（兼容手机端/微信可能缺失后缀或返回octet-stream）
    file_extension = _infer_excel_extension(file.filename or "", file.content_type or "", content)
    if not file_extension:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件格式无法识别，请上传Excel文件(.xlsx/.xls)"
        )
    if file.content_type and file.content_type.lower() not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {file.content_type}"
        )

    # 生成文件ID和路径
    file_id = f"file_{uuid.uuid4().hex[:12]}"
    timestamp = datetime.now().strftime("%Y%m")
    upload_dir = os.path.join(settings.UPLOAD_DIR, timestamp)
    os.makedirs(upload_dir, exist_ok=True)
    
    # 保存文件
    safe_filename = f"{file_id}{file_extension}"
    file_path = os.path.join(upload_dir, safe_filename)
    original_filename = (file.filename or "").strip() or f"{file_id}{file_extension}"
    
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
    
    # 创建数据库记录
    new_file = FileModel(
        id=file_id,
        user_id=current_user.id,
        file_name=original_filename,
        file_type=FileType.ORIGINAL,
        file_path=file_path,
        file_size=file_size,
        status=FileStatus.COMPLETED
    )
    
    db.add(new_file)
    await db.commit()
    await db.refresh(new_file)
    
    # 构建响应
    response_data = FileUploadResponse(
        fileId=new_file.id,
        fileName=new_file.file_name,
        fileSize=new_file.file_size,
        filePath=new_file.file_path,
        uploadTime=new_file.upload_time,
        status=new_file.status
    )
    
    return ApiResponse(
        code=200,
        message="上传成功",
        data=response_data.model_dump()
    )

@router.post("/process", response_model=ApiResponse)
async def process_file(
    request: FileProcessRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """处理Excel文件：按会计月汇总"""
    # 查找文件
    result = await db.execute(
        select(FileModel).where(
            FileModel.id == request.fileId,
            FileModel.user_id == current_user.id
        )
    )
    original_file = result.scalar_one_or_none()
    
    if not original_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    if not os.path.exists(original_file.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件已被删除"
        )
    
    try:
        # 更新状态为处理中
        original_file.status = FileStatus.PROCESSING
        await db.commit()
        
        # 处理Excel文件
        processor = ExcelProcessor(original_file.file_path)
        processor.load_file()
        result_data = processor.process_by_accounting_month()
        
        processed_df = result_data["df"]
        summary = result_data["summary"]
        
        # 生成处理后的文件
        processed_file_id = f"{original_file.id}_processed"
        processed_filename = f"{os.path.splitext(original_file.file_name)[0]}_处理后.xlsx"
        
        timestamp = datetime.now().strftime("%Y%m")
        upload_dir = os.path.join(settings.UPLOAD_DIR, timestamp)
        os.makedirs(upload_dir, exist_ok=True)
        
        processed_file_path = os.path.join(upload_dir, f"{processed_file_id}.xlsx")
        processor.save_processed_file(processed_file_path, processed_df)
        
        # 获取文件大小
        processed_file_size = os.path.getsize(processed_file_path)
        
        # 创建处理后文件的数据库记录
        processed_file = FileModel(
            id=processed_file_id,
            user_id=current_user.id,
            file_name=processed_filename,
            file_type=FileType.PROCESSED,
            file_path=processed_file_path,
            file_size=processed_file_size,
            original_file_id=original_file.id,
            process_time=datetime.now(),
            status=FileStatus.COMPLETED
        )
        
        db.add(processed_file)
        
        # 更新原文件状态
        original_file.status = FileStatus.COMPLETED
        original_file.process_time = datetime.now()
        
        await db.commit()
        await db.refresh(processed_file)
        
        # 构建响应
        response_data = FileProcessResponse(
            originalFileId=original_file.id,
            processedFileId=processed_file.id,
            processedFileName=processed_file.file_name,
            processedFilePath=processed_file.file_path,
            processTime=processed_file.process_time,
            status=processed_file.status,
            summary=summary
        )
        
        return ApiResponse(
            code=200,
            message="处理完成",
            data=response_data.model_dump()
        )
        
    except Exception as e:
        # 处理失败，更新状态
        original_file.status = FileStatus.FAILED
        await db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件处理失败: {str(e)}"
        )

@router.get("/download/{file_id}", response_model=ApiResponse)
async def get_download_url(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取文件下载链接"""
    # 查找文件
    result = await db.execute(
        select(FileModel).where(
            FileModel.id == file_id,
            FileModel.user_id == current_user.id
        )
    )
    file_record = result.scalar_one_or_none()
    
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    if not os.path.exists(file_record.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件已被删除"
        )
    
    # 生成下载URL（简化版，实际生产环境建议使用CDN或签名URL）
    download_url = f"/api/v1/files/direct-download/{file_id}"
    
    response_data = FileDownloadResponse(
        downloadUrl=download_url,
        expiresIn=3600
    )
    
    return ApiResponse(
        code=200,
        data=response_data.model_dump()
    )

@router.get("/direct-download/{file_id}")
async def direct_download(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """直接下载文件"""
    # 查找文件
    result = await db.execute(
        select(FileModel).where(
            FileModel.id == file_id,
            FileModel.user_id == current_user.id
        )
    )
    file_record = result.scalar_one_or_none()
    
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    if not os.path.exists(file_record.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件已被删除"
        )
    
    return FileResponse(
        path=file_record.file_path,
        filename=file_record.file_name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@router.get("/preview/{file_id}", response_model=ApiResponse)
async def preview_file(
    file_id: str,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """预览文件数据"""
    # 查找文件
    result = await db.execute(
        select(FileModel).where(
            FileModel.id == file_id,
            FileModel.user_id == current_user.id
        )
    )
    file_record = result.scalar_one_or_none()
    
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    if not os.path.exists(file_record.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件已被删除"
        )
    
    try:
        # 加载并预览数据
        processor = ExcelProcessor(file_record.file_path)
        processor.load_file()
        preview_data = processor.preview_data(page=page, page_size=pageSize)
        
        response_data = FilePreviewResponse(**preview_data)
        
        return ApiResponse(
            code=200,
            data=response_data.model_dump()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件预览失败: {str(e)}"
        )

@router.get("/history", response_model=ApiResponse)
async def get_file_history(
    type: Optional[str] = Query("all", regex="^(all|original|processed)$"),
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取文件历史列表"""
    # 构建查询
    query = select(FileModel).where(FileModel.user_id == current_user.id)
    
    if type != "all":
        file_type = FileType.ORIGINAL if type == "original" else FileType.PROCESSED
        query = query.where(FileModel.file_type == file_type)
    
    # 获取总数
    count_result = await db.execute(
        select(FileModel).where(FileModel.user_id == current_user.id)
    )
    total = len(count_result.scalars().all())
    
    # 分页查询
    query = query.order_by(desc(FileModel.upload_time))
    query = query.offset((page - 1) * pageSize).limit(pageSize)
    
    result = await db.execute(query)
    files = result.scalars().all()
    
    # 构建响应
    file_list = [
        FileHistoryItem(
            id=f.id,
            fileName=f.file_name,
            fileType=f.file_type,
            filePath=f.file_path,
            fileSize=f.file_size,
            uploadTime=f.upload_time,
            processTime=f.process_time,
            status=f.status
        )
        for f in files
    ]
    
    response_data = FileHistoryResponse(
        list=file_list,
        total=total,
        page=page,
        pageSize=pageSize
    )
    
    return ApiResponse(
        code=200,
        data=response_data.model_dump()
    )

@router.delete("/{file_id}", response_model=ApiResponse)
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除文件"""
    # 查找文件
    result = await db.execute(
        select(FileModel).where(
            FileModel.id == file_id,
            FileModel.user_id == current_user.id
        )
    )
    file_record = result.scalar_one_or_none()
    
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    # 删除物理文件
    if os.path.exists(file_record.file_path):
        try:
            os.remove(file_record.file_path)
        except:
            pass
    
    # 删除数据库记录
    await db.delete(file_record)
    await db.commit()
    
    return ApiResponse(
        code=200,
        message="删除成功"
    )

@router.delete("/history/clear", response_model=ApiResponse)
async def clear_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """清空所有历史"""
    # 查找所有文件
    result = await db.execute(
        select(FileModel).where(FileModel.user_id == current_user.id)
    )
    files = result.scalars().all()
    
    # 删除物理文件
    for file_record in files:
        if os.path.exists(file_record.file_path):
            try:
                os.remove(file_record.file_path)
            except:
                pass
    
    # 删除数据库记录
    await db.execute(
        delete(FileModel).where(FileModel.user_id == current_user.id)
    )
    await db.commit()
    
    return ApiResponse(
        code=200,
        message="清空成功"
    )
