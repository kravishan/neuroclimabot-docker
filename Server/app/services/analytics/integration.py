"""
Analytics integration with in-memory tracking.
Tracks chat interactions, documents, topics, and performance metrics.
"""

import logging
from typing import Dict, Any

from app.services.analytics.service import get_analytics_service

logger = logging.getLogger(__name__)


async def track_chat_analytics(
    query: str,
    response: Dict[str, Any],
    session_id: str,
    user_id: str,
    language: str,
    difficulty_level: str,
    response_time: float,
    conversation_type: str
) -> None:
    """
    Track chat analytics with in-memory storage.

    Args:
        query: The user's query
        response: The chat response dictionary
        session_id: The conversation session ID
        user_id: The user ID
        language: The response language
        difficulty_level: The difficulty level
        response_time: The response time in seconds
        conversation_type: "start" or "continue"
    """
    try:
        analytics = await get_analytics_service()

        # Track the query
        await analytics.track_query(
            query=query,
            session_id=session_id,
            user_id=user_id,
            language=language
        )

        # Track response time
        await analytics.track_response_time(response_time)

        # Extract and track document names from response
        if response and isinstance(response, dict):
            # Try to get document names from various possible locations
            doc_names = set()

            # Check for sources list (ChatResponse.sources)
            if "sources" in response and isinstance(response["sources"], list):
                for source in response["sources"]:
                    if isinstance(source, dict):
                        # Extract doc_name from Source object
                        if "doc_name" in source:
                            doc_names.add(source["doc_name"])
                        # Fallback to title if doc_name not found
                        elif "title" in source:
                            doc_names.add(source["title"])

            # Track all found documents
            for doc_name in doc_names:
                if doc_name:
                    await analytics.track_document(doc_name)

            # Extract and track topics from social_tipping_point
            topics = set()

            # Check for social_tipping_point (ChatResponse.social_tipping_point)
            if "social_tipping_point" in response and isinstance(response["social_tipping_point"], dict):
                stp = response["social_tipping_point"]

                # Only track qualifying factors as topics (not the main text which is too long)
                if "qualifying_factors" in stp and isinstance(stp["qualifying_factors"], list):
                    for factor in stp["qualifying_factors"]:
                        if factor and isinstance(factor, str):
                            # Extract the factor name (before the colon)
                            # E.g., "Environmental problems with perceived societal consequences: Strong, ..."
                            factor_name = factor.split(':')[0].strip() if ':' in factor else factor.strip()
                            # Only track if it's a reasonable length (not a full paragraph)
                            if factor_name and len(factor_name) <= 100:
                                topics.add(factor_name)

            # Track all found topics
            for topic in topics:
                if topic and topic.strip():
                    await analytics.track_topic(topic.strip())

        logger.info(
            f"Analytics tracked: session={session_id}, "
            f"type={conversation_type}, lang={language}, time={response_time:.2f}s"
        )

    except Exception as e:
        logger.error(f"Failed to track analytics: {e}", exc_info=True)
