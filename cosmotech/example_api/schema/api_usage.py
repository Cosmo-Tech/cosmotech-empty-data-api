from datetime import datetime

from sqlmodel import Field, Index

from cosmotech.example_api.schema.model import SQLModel
from cosmotech.example_api.utils.datetime import utcnow


class ApiUsage(SQLModel, table=True):
    """Database model for tracking API usage per user per endpoint."""

    __tablename__ = "api_usage"
    __table_args__ = (
        Index("ix_api_usage_user_timestamp", "user_id", "timestamp"),
        Index("ix_api_usage_route_timestamp", "route", "timestamp"),
        Index("ix_api_usage_timestamp", "timestamp"),
    )

    id: int | None = Field(default=None, primary_key=True, description="Auto-increment primary key")
    user_id: str = Field(max_length=255, index=False, description="User ID from JWT 'sub' claim")
    user_name: str = Field(max_length=255, index=False, description="User name from JWT 'name' claim")
    method: str = Field(max_length=10, description="HTTP method (GET, POST, PATCH, DELETE, etc.)")
    endpoint: str = Field(max_length=2048, description="Actual request path, e.g. /value_framework/VF-abc123")
    route: str = Field(max_length=2048, description="Matched route pattern, e.g. /value_framework/{value_framework_id}")
    status_code: int = Field(description="HTTP response status code")
    response_time_ms: float = Field(description="Response time in milliseconds")
    timestamp: datetime = Field(default_factory=utcnow, nullable=False, description="UTC timestamp of the request")


class ApiUsageResponse(SQLModel):
    """Schema for ApiUsage responses."""

    id: int
    user_id: str
    user_name: str
    method: str
    endpoint: str
    route: str
    status_code: int
    response_time_ms: float
    timestamp: datetime


class ApiUsageSummaryByUser(SQLModel):
    """Aggregated usage summary per user."""

    user_id: str
    user_name: str
    request_count: int


class ApiUsageSummaryByEndpoint(SQLModel):
    """Aggregated usage summary per route."""

    route: str
    method: str
    request_count: int
