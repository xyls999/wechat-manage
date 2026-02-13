from datetime import datetime, timedelta
import os
from typing import Dict

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import File as FileModel


async def cleanup_expired_files(db: AsyncSession, retention_days: int) -> Dict[str, int]:
    cutoff = datetime.utcnow() - timedelta(days=retention_days)

    result = await db.execute(
        select(FileModel).where(
            and_(
                FileModel.upload_time.is_not(None),
                FileModel.upload_time < cutoff,
            )
        )
    )
    files = result.scalars().all()

    deleted_records = 0
    deleted_physical_files = 0
    failed_physical_deletes = 0

    for file_record in files:
        if file_record.file_path and os.path.exists(file_record.file_path):
            try:
                os.remove(file_record.file_path)
                deleted_physical_files += 1
            except Exception:
                failed_physical_deletes += 1

        await db.delete(file_record)
        deleted_records += 1

    await db.commit()

    return {
        "deletedRecords": deleted_records,
        "deletedPhysicalFiles": deleted_physical_files,
        "failedPhysicalDeletes": failed_physical_deletes,
    }
