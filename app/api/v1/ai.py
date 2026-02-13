from fastapi import APIRouter, HTTPException, status
import httpx

from app.core.config import settings
from app.schemas.ai import ChatRequest, ChatResponse
from app.schemas.response import ApiResponse

router = APIRouter()


@router.post("/chat", response_model=ApiResponse)
async def ai_chat(payload: ChatRequest):
    if not settings.AI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AI_API_KEY 未配置，请在环境变量中设置",
        )

    model = payload.model or settings.AI_MODEL
    base_url = settings.AI_BASE_URL.rstrip("/")
    url = f"{base_url}/chat/completions"

    req_body = {
        "model": model,
        "messages": [m.model_dump() for m in payload.messages],
        "temperature": payload.temperature,
    }
    if payload.max_tokens is not None:
        req_body["max_tokens"] = payload.max_tokens

    try:
        async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {settings.AI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=req_body,
            )
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise HTTPException(status_code=502, detail="AI 接口返回空结果")
        reply = choices[0].get("message", {}).get("content", "")

        output = ChatResponse(model=model, reply=reply)
        return ApiResponse(code=200, data=output.model_dump())
    except httpx.HTTPStatusError as e:
        detail = e.response.text if e.response is not None else str(e)
        raise HTTPException(status_code=502, detail=f"AI 请求失败: {detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 服务异常: {str(e)}")
