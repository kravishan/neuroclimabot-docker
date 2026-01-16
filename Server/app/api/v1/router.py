"""Main API router with auth endpoints."""

from fastapi import APIRouter

from app.api.v1 import admin, chat, health, feedback, graph, analytics, auth, external, questionnaire

api_router = APIRouter()

# Include sub-routers - ORDER MATTERS
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["Health"]
)

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    chat.router,
    prefix="/chat", 
    tags=["Chat"]
)

api_router.include_router(
    feedback.router,
    prefix="/feedback",
    tags=["Feedback"]
)

api_router.include_router(
    questionnaire.router,
    prefix="/questionnaire",
    tags=["Research Questionnaire"]
)

api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["Admin"]
)

api_router.include_router(
    graph.router,
    prefix="/graph-viz",
    tags=["Graph Visualization"]
)

api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Analytics"]
)

api_router.include_router(
    external.router,
    prefix="/external",
    tags=["External Document API"]
)