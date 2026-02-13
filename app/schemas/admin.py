from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List

from app.models.file import FileType, FileStatus


class AdminUserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    password: str = Field(..., min_length=6, max_length=20)
    nickname: str = Field(..., min_length=1, max_length=20)
    is_active: bool = True
    is_admin: bool = False


class AdminUserUpdate(BaseModel):
    nickname: Optional[str] = Field(default=None, min_length=1, max_length=20)
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    reset_password: Optional[str] = Field(default=None, min_length=6, max_length=20)


class AdminUserItem(BaseModel):
    id: str
    username: str
    nickname: str
    avatar: str
    isActive: bool
    isAdmin: bool
    createdAt: datetime
    lastLoginAt: Optional[datetime]


class AdminUserListResponse(BaseModel):
    list: List[AdminUserItem]
    total: int
    page: int
    pageSize: int


class AdminUserDetailResponse(BaseModel):
    user: AdminUserItem
    fileCount: int
    totalFileSize: int


class AdminFileUpdate(BaseModel):
    remark: Optional[str] = Field(default=None, max_length=255)
    status: Optional[FileStatus] = None


class AdminFileItem(BaseModel):
    id: str
    userId: str
    username: Optional[str]
    fileName: str
    fileType: FileType
    filePath: str
    fileSize: int
    status: FileStatus
    uploadTime: datetime
    processTime: Optional[datetime]
    remark: str


class AdminFileListResponse(BaseModel):
    list: List[AdminFileItem]
    total: int
    page: int
    pageSize: int


class AdminFileBatchDeleteRequest(BaseModel):
    fileIds: List[str] = Field(..., min_length=1)


class AdminStatsResponse(BaseModel):
    totalUsers: int
    totalFiles: int
    totalStorageBytes: int
    uploadsLast7Days: int


class CleanupConfigResponse(BaseModel):
    retentionDays: int
    scheduleHour: int
    scheduleMinute: int


class CleanupRunResponse(BaseModel):
    deletedRecords: int
    deletedPhysicalFiles: int
    failedPhysicalDeletes: int
