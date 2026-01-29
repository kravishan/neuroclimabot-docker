"""
Analytics API endpoints combining Redis and MongoDB data.

Data sources:
- Redis (DB 2): Popular queries (max 10), documents (max 10), trending keywords (max 20)
- MongoDB: Feedback stats, session stats (total_sessions, avg_response_time)
"""

from typing import Any
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.services.analytics.service import get_analytics_service, RedisAnalyticsService
from app.services.database.stats_database import get_stats_database, StatsDatabase
from app.config.database import get_redis_config

router = APIRouter()
redis_config = get_redis_config()


class AnalyticsResponse(BaseModel):
    success: bool
    data: Any


@router.get("/popular-queries", response_model=AnalyticsResponse)
async def get_popular_queries(
    limit: int = Query(default=10, ge=1, le=10, description="Max 10 queries"),
    analytics: RedisAnalyticsService = Depends(get_analytics_service)
):
    """Get popular queries (max 10)"""
    try:
        # Enforce max limit from config
        effective_limit = min(limit, redis_config.POPULAR_QUERIES_LIMIT)
        queries = await analytics.get_popular_queries(effective_limit)
        return AnalyticsResponse(success=True, data=queries)
    except Exception as e:
        return AnalyticsResponse(success=False, data={"error": str(e)})


@router.get("/popular-documents", response_model=AnalyticsResponse)
async def get_popular_documents(
    limit: int = Query(default=10, ge=1, le=10, description="Max 10 documents"),
    analytics: RedisAnalyticsService = Depends(get_analytics_service)
):
    """Get popular documents (max 10)"""
    try:
        # Enforce max limit from config
        effective_limit = min(limit, redis_config.POPULAR_DOCUMENTS_LIMIT)
        documents = await analytics.get_popular_documents(effective_limit)
        return AnalyticsResponse(success=True, data=documents)
    except Exception as e:
        return AnalyticsResponse(success=False, data={"error": str(e)})


@router.get("/trending-topics", response_model=AnalyticsResponse)
async def get_trending_topics(
    limit: int = Query(default=20, ge=1, le=20, description="Max 20 keywords"),
    analytics: RedisAnalyticsService = Depends(get_analytics_service)
):
    """Get trending keywords/topics (max 20)"""
    try:
        # Enforce max limit from config
        effective_limit = min(limit, redis_config.TRENDING_KEYWORDS_LIMIT)
        topics = await analytics.get_trending_topics(effective_limit)
        return AnalyticsResponse(success=True, data=topics)
    except Exception as e:
        return AnalyticsResponse(success=False, data={"error": str(e)})


@router.get("/topic-distribution", response_model=AnalyticsResponse)
async def get_topic_distribution(
    analytics: RedisAnalyticsService = Depends(get_analytics_service)
):
    """Get topic distribution"""
    try:
        distribution = await analytics.get_topic_distribution()
        return AnalyticsResponse(success=True, data=distribution)
    except Exception as e:
        return AnalyticsResponse(success=False, data={"error": str(e)})


@router.get("/stats", response_model=AnalyticsResponse)
async def get_today_stats(
    analytics: RedisAnalyticsService = Depends(get_analytics_service)
):
    """
    Get today's analytics statistics.

    Combines data from:
    - Redis: total_queries, unique_users, total_documents, total_topics
    - MongoDB: total_sessions, avg_response_time
    """
    try:
        # Get stats from Redis
        redis_stats = await analytics.get_today_stats()

        # Get session stats from MongoDB
        stats_db = await get_stats_database()
        session_stats = await stats_db.get_session_stats()

        # Combine stats
        combined_stats = {
            "total_queries": redis_stats.get("total_queries", 0),
            "unique_users": redis_stats.get("unique_users", 0),
            "total_documents": redis_stats.get("total_documents", 0),
            "total_topics": redis_stats.get("total_topics", 0),
            "total_sessions": session_stats.get("total_sessions", 0),
            "avg_response_time": round(session_stats.get("avg_response_time", 0.0), 2)
        }

        return AnalyticsResponse(success=True, data=combined_stats)
    except Exception as e:
        return AnalyticsResponse(success=False, data={"error": str(e)})


@router.get("/dashboard", response_model=AnalyticsResponse)
async def get_dashboard_data(
    limit: int = Query(default=10, ge=1, le=10, description="Limit for queries/documents (max 10)"),
    analytics: RedisAnalyticsService = Depends(get_analytics_service)
):
    """
    Get complete dashboard data in one request.

    Data sources:
    - Redis: popular_queries (max 10), popular_documents (max 10), trending_topics (max 20)
    - MongoDB: feedback_stats, session stats (total_sessions, avg_response_time)
    """
    try:
        # Enforce limits
        queries_limit = min(limit, redis_config.POPULAR_QUERIES_LIMIT)
        documents_limit = min(limit, redis_config.POPULAR_DOCUMENTS_LIMIT)
        topics_limit = redis_config.TRENDING_KEYWORDS_LIMIT  # Always max 20

        # Get Redis data
        popular_queries = await analytics.get_popular_queries(queries_limit)
        popular_documents = await analytics.get_popular_documents(documents_limit)
        trending_topics = await analytics.get_trending_topics(topics_limit)
        topic_distribution = await analytics.get_topic_distribution()
        redis_stats = await analytics.get_today_stats()

        # Get MongoDB data
        stats_db = await get_stats_database()
        feedback_stats = await stats_db.get_feedback_stats()
        session_stats = await stats_db.get_session_stats()

        # Combine stats from Redis and MongoDB
        combined_stats = {
            "total_queries": redis_stats.get("total_queries", 0),
            "unique_users": redis_stats.get("unique_users", 0),
            "total_documents": redis_stats.get("total_documents", 0),
            "total_topics": redis_stats.get("total_topics", 0),
            "total_sessions": session_stats.get("total_sessions", 0),
            "avg_response_time": round(session_stats.get("avg_response_time", 0.0), 2)
        }

        dashboard_data = {
            "popular_queries": popular_queries,
            "popular_documents": popular_documents,
            "trending_topics": trending_topics,
            "topic_distribution": topic_distribution,
            "stats": combined_stats,
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
    conversation_type: str = "continue"  # "start" or "continue"
    language: str = None


@router.post("/feedback")
async def track_feedback(request: FeedbackRequest):
    """
    Track user feedback (thumbs up/down).

    Feedback is stored in MongoDB for persistence.
    """
    try:
        # Map "up"/"down" to "thumbs_up"/"thumbs_down" for MongoDB
        feedback_type_map = {"up": "thumbs_up", "down": "thumbs_down"}
        internal_type = feedback_type_map.get(request.feedback_type, request.feedback_type)

        # Store in MongoDB
        stats_db = await get_stats_database()
        await stats_db.add_feedback(
            response_id=request.message_id,
            feedback_type=internal_type,
            conversation_type=request.conversation_type,
            language=request.language
        )

        return AnalyticsResponse(
            success=True,
            data={"message": "Feedback tracked successfully"}
        )
    except Exception as e:
        return AnalyticsResponse(success=False, data={"error": str(e)})


@router.get("/feedback-stats", response_model=AnalyticsResponse)
async def get_feedback_stats():
    """Get feedback statistics from MongoDB"""
    try:
        stats_db = await get_stats_database()
        stats = await stats_db.get_feedback_stats()
        return AnalyticsResponse(success=True, data=stats)
    except Exception as e:
        return AnalyticsResponse(success=False, data={"error": str(e)})


@router.get("/session-stats", response_model=AnalyticsResponse)
async def get_session_stats():
    """Get session statistics from MongoDB"""
    try:
        stats_db = await get_stats_database()
        stats = await stats_db.get_session_stats()
        return AnalyticsResponse(success=True, data=stats)
    except Exception as e:
        return AnalyticsResponse(success=False, data={"error": str(e)})
