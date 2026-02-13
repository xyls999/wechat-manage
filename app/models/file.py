from sqlalchemy import Column, String, Integer, DateTime, Enum, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base
import enum
import uuid

class FileType(str, enum.Enum):
    ORIGINAL = "original"
    PROCESSED = "processed"

class FileStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class File(Base):
    __tablename__ = "files"
    
    id = Column(String(50), primary_key=True, default=lambda: f"file_{uuid.uuid4().hex[:12]}")
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(Enum(FileType), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    original_file_id = Column(String(50), nullable=True)
    upload_time = Column(DateTime(timezone=True), server_default=func.now())
    process_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(FileStatus), default=FileStatus.PENDING)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    remark = Column(String(255), default="", nullable=False)
