"""
Redis-only analytics API endpoints with dynamic topic modeling
"""

from typing import Any
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.services.analytics.service import get_analytics_service, RedisAnalyticsService


router = APIRouter()


class AnalyticsResponse(BaseModel):
    success: bool
    data: Any


@router.get("/popular-queries", response_model=AnalyticsResponse)
async def get_popular_queries(
    limit: int = Query(10, ge=1, le=50),
    analytics: RedisAnalyticsService = Depends(get_analytics_service)
):
    """Get today's popular queries with topic information"""
    try:
        queries = await analytics.get_popular_queries(limit)
        return AnalyticsResponse(success=True, data=queries)
    except Exception as e:
        return AnalyticsResponse(success=False, data={"error": str(e)})


@router.get("/popular-documents", response_model=AnalyticsResponse)
async def get_popular_documents(
    limit: int = Query(10, ge=1, le=50),
    analytics: RedisAnalyticsService = Depends(get_analytics_service)
):
    """Get today's most referenced documents"""
    try:
        documents = await analytics.get_popular_documents(limit)
        return AnalyticsResponse(success=True, data=documents)
    except Exception as e:
        return AnalyticsResponse(success=False, data={"error": str(e)})


@router.get("/trending-topics", response_model=AnalyticsResponse)
async def get_trending_topics(
    limit: int = Query(10, ge=1, le=20),
    analytics: RedisAnalyticsService = Depends(get_analytics_service)
):
    """Get today's trending topics with auto-generated names"""
    try:
        topics = await analytics.get_trending_topics(limit)
        return AnalyticsResponse(success=True, data=topics)
    except Exception as e:
        return AnalyticsResponse(success=False, data={"error": str(e)})


@router.get("/topic-distribution", response_model=AnalyticsResponse)
async def get_topic_distribution(
    analytics: RedisAnalyticsService = Depends(get_analytics_service)
):
    """Get topic distribution for today"""
    try:
        distribution = await analytics.get_topic_distribution()
        return AnalyticsResponse(success=True, data=distribution)
    except Exception as e:
        return AnalyticsResponse(success=False, data={"error": str(e)})


@router.get("/stats", response_model=AnalyticsResponse)
async def get_today_stats(
    analytics: RedisAnalyticsService = Depends(get_analytics_service)
):
    """Get today's analytics statistics with topic information"""
    try:
        stats = await analytics.get_today_stats()
        return AnalyticsResponse(success=True, data=stats)
    except Exception as e:
        return AnalyticsResponse(success=False, data={"error": str(e)})


@router.get("/dashboard", response_model=AnalyticsResponse)
async def get_dashboard_data(
    limit: int = Query(10, ge=1, le=50),
    analytics: RedisAnalyticsService = Depends(get_analytics_service)
):
    """Get complete dashboard data with topics in one request"""
    try:
        # Get all dashboard data at once
        popular_queries = await analytics.get_popular_queries(limit)
        popular_documents = await analytics.get_popular_documents(limit)
        trending_topics = await analytics.get_trending_topics(limit)
        topic_distribution = await analytics.get_topic_distribution()
        stats = await analytics.get_today_stats()
        feedback_stats = await analytics.get_feedback_stats()

        dashboard_data = {
            "popular_queries": popular_queries,
            "popular_documents": popular_documents,
            "trending_topics": trending_topics,
            "topic_distribution": topic_distribution,
            "stats": stats,
            "feedback_stats": feedback_stats,
            "period": "today"
        }

        return AnalyticsResponse(success=True, data=dashboard_data)
    except Exception as e:
        return AnalyticsResponse(success=False, data={"error": str(e)})


class FeedbackRequest(BaseModel):
    """Feedback request model"""
    feedback_type: str  # "up" or "down"
    message_id: str
    user_id: str = "anonymous"
    session_id: str = None


@router.post("/feedback")
async def track_feedback(
    request: FeedbackRequest,
    analytics: RedisAnalyticsService = Depends(get_analytics_service)
):
    """
    Track user feedback (thumbs up/down).

    For the same message_id + user_id, only the last feedback is saved.
    Different responses will have their feedback counted separately.
    """
    try:
        # Map "up"/"down" to "positive"/"negative"
        feedback_type_map = {"up": "positive", "down": "negative"}
        internal_type = feedback_type_map.get(request.feedback_type, request.feedback_type)

        await analytics.track_feedback(
            feedback_type=internal_type,
            message_id=request.message_id,
            user_id=request.user_id,
            session_id=request.session_id
        )

        return AnalyticsResponse(
            success=True,
            data={"message": "Feedback tracked successfully"}
        )
    except Exception as e:
        return AnalyticsResponse(success=False, data={"error": str(e)})


@router.get("/feedback-stats", response_model=AnalyticsResponse)
async def get_feedback_stats(
    analytics: RedisAnalyticsService = Depends(get_analytics_service)
):
    """Get feedback statistics"""
    try:
        stats = await analytics.get_feedback_stats()
        return AnalyticsResponse(success=True, data=stats)
    except Exception as e:
        return AnalyticsResponse(success=False, data={"error": str(e)})