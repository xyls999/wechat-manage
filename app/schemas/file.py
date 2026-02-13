from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.file import FileType, FileStatus

# 文件上传响应
class FileUploadResponse(BaseModel):
    fileId: str
    fileName: str
    fileSize: int
    filePath: str
    uploadTime: datetime
    status: FileStatus
    
    class Config:
        from_attributes = True

# 文件处理请求
class FileProcessRequest(BaseModel):
    fileId: str = Field(..., description="待处理的文件ID")

# 文件处理响应
class FileProcessResponse(BaseModel):
    originalFileId: str
    processedFileId: str
    processedFileName: str
    processedFilePath: str
    processTime: datetime
    status: FileStatus
    summary: Dict[str, Any]
    
    class Config:
        from_attributes = True

# 文件下载响应
class FileDownloadResponse(BaseModel):
    downloadUrl: str
    expiresIn: int = 3600

# 文件预览响应
class FilePreviewResponse(BaseModel):
    columns: List[str]
    rows: List[Dict[str, Any]]
    total: int
    page: int
    pageSize: int

# 文件历史列表项
class FileHistoryItem(BaseModel):
    id: str
    fileName: str
    fileType: FileType
    filePath: str
    fileSize: int
    uploadTime: datetime
    processTime: Optional[datetime] = None
    status: FileStatus
    
    class Config:
        from_attributes = True

# 文件历史列表响应
class FileHistoryResponse(BaseModel):
    list: List[FileHistoryItem]
    total: int
    page: int
    pageSize: int
