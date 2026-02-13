from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"
    
    # JWT配置
    SECRET_KEY: str = "your-secret-key-change-in-production-min-32-characters-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24小时
    
    # 文件存储
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # 管理后台配置
    ADMIN_AUTH_ENABLED: bool = False
    ADMIN_ALLOWED_ORIGINS: List[str] = ["*"]

    # 清理任务配置
    CLEANUP_RETENTION_DAYS: int = 3
    CLEANUP_SCHEDULE_HOUR: int = 3
    CLEANUP_SCHEDULE_MINUTE: int = 0

    # AI 机器人配置（OpenAI 兼容接口）
    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://api.openai.com/v1"
    AI_MODEL: str = "gpt-4o-mini"
    AI_TIMEOUT_SECONDS: int = 60
    
    class Config:
        env_file = ".env"

settings = Settings()
