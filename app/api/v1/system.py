from fastapi import APIRouter

from app.core.config import settings
from app.schemas.response import ApiResponse

router = APIRouter()


@router.get("/info", response_model=ApiResponse)
async def get_system_info():
    return ApiResponse(
        code=200,
        data={
            "service": "智慧表格助手 API",
            "version": "1.0.0",
            "adminAuthEnabled": settings.ADMIN_AUTH_ENABLED,
            "cleanupRetentionDays": settings.CLEANUP_RETENTION_DAYS,
            "aiConfigured": bool(settings.AI_API_KEY),
            "aiBaseUrl": settings.AI_BASE_URL,
            "aiModel": settings.AI_MODEL,
        },
    )
