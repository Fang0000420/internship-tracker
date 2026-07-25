from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]


@router.get("/health")
def get_health() -> HealthResponse:
    # TODO: 返回符合 HealthResponse 契约的健康状态
    return HealthResponse(status="ok")
