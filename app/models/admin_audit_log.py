from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id = Column(String(50), primary_key=True, default=lambda: f"audit_{uuid.uuid4().hex[:12]}")
    actor = Column(String(100), nullable=False, default="system")
    action = Column(String(100), nullable=False)
    target_type = Column(String(50), nullable=False)
    target_id = Column(String(50), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
