from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def ensure_sqlite_compat(engine: AsyncEngine) -> None:
    dialect_name = engine.url.get_backend_name()
    if dialect_name != "sqlite":
        return

    async with engine.begin() as conn:
        users_cols = await conn.execute(text("PRAGMA table_info(users)"))
        user_columns = {row[1] for row in users_cols.fetchall()}
        if "is_active" not in user_columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"))
        if "is_admin" not in user_columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"))
        if "last_login_at" not in user_columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN last_login_at DATETIME"))

        files_cols = await conn.execute(text("PRAGMA table_info(files)"))
        file_columns = {row[1] for row in files_cols.fetchall()}
        if "deleted_at" not in file_columns:
            await conn.execute(text("ALTER TABLE files ADD COLUMN deleted_at DATETIME"))
        if "remark" not in file_columns:
            await conn.execute(text("ALTER TABLE files ADD COLUMN remark VARCHAR(255) NOT NULL DEFAULT ''"))

        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS admin_audit_logs (
                    id VARCHAR(50) PRIMARY KEY,
                    actor VARCHAR(100) NOT NULL,
                    action VARCHAR(100) NOT NULL,
                    target_type VARCHAR(50) NOT NULL,
                    target_id VARCHAR(50) NOT NULL,
                    details TEXT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
