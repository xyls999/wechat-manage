from pydantic import BaseModel
from typing import Optional, Any

class ApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Optional[Any] = None
