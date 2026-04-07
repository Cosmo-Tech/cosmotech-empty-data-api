from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlmodel import select

from cosmotech.example_api.schema import SessionDep
from cosmotech.example_api.schema.api_usage import (
    ApiUsage,
    ApiUsageResponse,
    ApiUsageSummaryByEndpoint,
    ApiUsageSummaryByUser,
)
from cosmotech.example_api.utils.oauth2 import valid_admin_token

usage_router = APIRouter(prefix="/usage", tags=["Usage (Admin)"])


@usage_router.get(
    "/",
    response_model=list[ApiUsageResponse],
    summary="List API usage records",
    responses={
        200: {"description": "List of API usage records"},
        403: {"description": "Admin access required"},
    },
)
async def get_usage_records(
    token: Annotated[dict, Depends(valid_admin_token)],
    session: SessionDep,
    user_id: str | None = Query(default=None, description="Filter by user ID"),
    route: str | None = Query(default=None, description="Filter by route pattern"),
    method: str | None = Query(default=None, description="Filter by HTTP method"),
    date_from: datetime | None = Query(default=None, description="Filter records from this UTC datetime (inclusive)"),
    date_to: datetime | None = Query(default=None, description="Filter records up to this UTC datetime (inclusive)"),
    offset: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, le=1000, ge=1, description="Max number of records to return"),
):
    """Retrieve a paginated, filterable list of API usage records. Requires Platform.Admin role."""
    stmt = select(ApiUsage)
    if user_id:
        stmt = stmt.where(ApiUsage.user_id == user_id)
    if route:
        stmt = stmt.where(ApiUsage.route == route)
    if method:
        stmt = stmt.where(ApiUsage.method == method.upper())
    if date_from:
        stmt = stmt.where(ApiUsage.timestamp >= date_from)
    if date_to:
        stmt = stmt.where(ApiUsage.timestamp <= date_to)
    stmt = stmt.order_by(ApiUsage.timestamp.desc()).offset(offset).limit(limit)
    return session.exec(stmt).all()


@usage_router.get(
    "/summary/by_user",
    response_model=list[ApiUsageSummaryByUser],
    summary="Get request count summary per user",
    responses={
        200: {"description": "Aggregated request counts per user"},
        403: {"description": "Admin access required"},
    },
)
async def get_usage_summary_by_user(
    token: Annotated[dict, Depends(valid_admin_token)],
    session: SessionDep,
    date_from: datetime | None = Query(default=None, description="Filter records from this UTC datetime (inclusive)"),
    date_to: datetime | None = Query(default=None, description="Filter records up to this UTC datetime (inclusive)"),
):
    """Retrieve the total number of requests per user. Requires Platform.Admin role."""
    stmt = select(ApiUsage.user_id, ApiUsage.user_name, func.count(ApiUsage.id).label("request_count")).group_by(
        ApiUsage.user_id, ApiUsage.user_name
    )
    if date_from:
        stmt = stmt.where(ApiUsage.timestamp >= date_from)
    if date_to:
        stmt = stmt.where(ApiUsage.timestamp <= date_to)
    stmt = stmt.order_by(func.count(ApiUsage.id).desc())
    rows = session.exec(stmt).all()
    return [ApiUsageSummaryByUser(user_id=r[0], user_name=r[1], request_count=r[2]) for r in rows]


@usage_router.get(
    "/summary/by_endpoint",
    response_model=list[ApiUsageSummaryByEndpoint],
    summary="Get request count summary per endpoint",
    responses={
        200: {"description": "Aggregated request counts per endpoint"},
        403: {"description": "Admin access required"},
    },
)
async def get_usage_summary_by_endpoint(
    token: Annotated[dict, Depends(valid_admin_token)],
    session: SessionDep,
    date_from: datetime | None = Query(default=None, description="Filter records from this UTC datetime (inclusive)"),
    date_to: datetime | None = Query(default=None, description="Filter records up to this UTC datetime (inclusive)"),
):
    """Retrieve the total number of requests per route and method. Requires Platform.Admin role."""
    stmt = select(ApiUsage.route, ApiUsage.method, func.count(ApiUsage.id).label("request_count")).group_by(
        ApiUsage.route, ApiUsage.method
    )
    if date_from:
        stmt = stmt.where(ApiUsage.timestamp >= date_from)
    if date_to:
        stmt = stmt.where(ApiUsage.timestamp <= date_to)
    stmt = stmt.order_by(func.count(ApiUsage.id).desc())
    rows = session.exec(stmt).all()
    return [ApiUsageSummaryByEndpoint(route=r[0], method=r[1], request_count=r[2]) for r in rows]
