from pydantic import BaseModel, Field
from datetime import datetime, timezone


class UserRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=5000,
        description="A user message to agent"
    )
    thread_id: str = Field(
        default="Default",
        description="A user conversational ID"
    )


class ChatResponse(BaseModel):
    response: str
    thread_id: str
    cached: bool = False
    model_used: str
    processing_time: float
    time_stamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class MetricsCollection(BaseModel):
    total_request: int
    total_error: int
    error_rate: float
    latency_sum: float
    cache_hit_rate: float
    latency_count: int
    input_token: int
    output_token: int


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    user_id: str | None = None
