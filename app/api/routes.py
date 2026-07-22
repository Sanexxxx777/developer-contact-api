from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies import get_client_identity, get_contact_service
from app.models.contact import ContactCreate, ContactResponse, HealthResponse, MetricsResponse
from app.services.contact_service import ContactService

router = APIRouter(prefix="/api")


@router.post(
    "/contact",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit the contact form",
    responses={429: {"description": "Rate limit exceeded"}, 503: {"description": "Email failed"}},
)
async def create_contact(
    payload: ContactCreate,
    service: Annotated[ContactService, Depends(get_contact_service)],
    identity: Annotated[str, Depends(get_client_identity)],
) -> ContactResponse:
    return await service.submit(payload, identity)


@router.get("/health", response_model=HealthResponse, summary="Service health")
async def health(request: Request) -> HealthResponse:
    database_ok = request.app.state.contact_repository.ping()
    return HealthResponse(
        status="ok" if database_ok else "degraded",
        database="ok" if database_ok else "unavailable",
    )


@router.get("/metrics", response_model=MetricsResponse, summary="Anonymous contact statistics")
async def metrics(request: Request) -> MetricsResponse:
    return MetricsResponse(**request.app.state.contact_repository.metrics())
