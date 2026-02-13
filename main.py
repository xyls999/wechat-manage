from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.core.database import engine, Base, AsyncSessionLocal
from app.api.v1 import auth, files, admin, system, ai
from app.services.cleanup import cleanup_expired_files
from app.services.schema_bootstrap import ensure_sqlite_compat

# 创建上传目录
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs("./static", exist_ok=True)
os.makedirs("./templates/admin", exist_ok=True)

templates = Jinja2Templates(directory="templates")
scheduler = AsyncIOScheduler()


async def _run_cleanup_job():
    async with AsyncSessionLocal() as session:
        await cleanup_expired_files(session, settings.CLEANUP_RETENTION_DAYS)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ensure_sqlite_compat(engine)

    scheduler.add_job(
        _run_cleanup_job,
        "cron",
        hour=settings.CLEANUP_SCHEDULE_HOUR,
        minute=settings.CLEANUP_SCHEDULE_MINUTE,
        id="cleanup_job",
        replace_existing=True,
    )
    scheduler.start()
    yield
    # 关闭时清理资源
    scheduler.shutdown(wait=False)
    await engine.dispose()

app = FastAPI(
    title="智慧表格助手 API",
    description="Excel文件处理与管理系统",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录
if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
if os.path.exists("./static"):
    app.mount("/static", StaticFiles(directory="./static"), name="static")

# 注册路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(files.router, prefix="/api/v1/files", tags=["文件处理"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["后台管理"])
app.include_router(system.router, prefix="/api/v1/system", tags=["系统"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["AI"])

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("admin/index.html", {"request": request})

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
