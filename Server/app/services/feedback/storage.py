import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

import redis.asyncio as redis
from app.config.database import get_redis_config
from app.schemas.feedback import ResponseFeedback, FeedbackStats, ThumbsFeedback
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SimpleFeedbackService:
    """Simple Redis-based service for thumbs up/down feedback."""
    
    def __init__(self):
        self.config = get_redis_config()
        self.redis_client = None
        self.is_connected = False
        
        # Redis keys
        self.feedback_key = "feedback:{feedback_id}"
        self.response_feedback_key = "response_feedback:{response_id}"
        self.daily_stats_key = "daily_feedback:{date}"
        self.global_stats_key = "global_feedback_stats"
        
        # Simple duplicate prevention
        self.session_feedback_key = "session_feedback:{session_id}:{response_id}"
    
    async def initialize(self):
        """Initialize Redis connection."""
        try:
            connection_kwargs = self.config.connection_kwargs
            self.redis_client = redis.from_url(**connection_kwargs)
            
            await self.redis_client.ping()
            self.is_connected = True
            logger.info("✅ Simple feedback service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize feedback service: {e}")
            raise
    
    async def submit_feedback(
        self,
        response_id: str,
        feedback_type: str,
        session_id: Optional[UUID] = None,
        response_language: str = "en",
        conversation_type: str = "unknown"
    ) -> bool:
        """Submit thumbs feedback."""
        
        if not self.is_connected:
            await self.initialize()
        
        try:
            feedback = ThumbsFeedback.UP if feedback_type.lower() == "up" else ThumbsFeedback.DOWN
            
            # Simple duplicate prevention using session
            if session_id:
                duplicate_key = self.session_feedback_key.format(
                    session_id=session_id, 
                    response_id=response_id
                )
                if await self.redis_client.exists(duplicate_key):
                    logger.info(f"Duplicate feedback prevented for response {response_id}")
                    return False
            
            # Create feedback record
            feedback_record = ResponseFeedback(
                response_id=response_id,
                session_id=session_id,
                feedback=feedback,
                user_id="anonymous",
                response_language=response_language,
                conversation_type=conversation_type
            )
            
            # Store individual feedback record
            feedback_key = self.feedback_key.format(feedback_id=feedback_record.id)
            feedback_data = feedback_record.model_dump(mode='json')
            feedback_data['created_at'] = feedback_record.created_at.isoformat()
            
            await self.redis_client.set(feedback_key, json.dumps(feedback_data))
            
            # Add to response feedback list
            response_key = self.response_feedback_key.format(response_id=response_id)
            await self.redis_client.lpush(response_key, str(feedback_record.id))
            
            # Mark session feedback to prevent duplicates
            if session_id:
                await self.redis_client.setex(duplicate_key, 3600, "submitted")
            
            # Update statistics
            await self._update_stats(feedback_record)
            
            logger.info(f"✅ Recorded {feedback.value} feedback for response {response_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit feedback: {e}")
            return False
    
    async def _update_stats(self, feedback: ResponseFeedback):
        """Update aggregated statistics."""
        
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            daily_key = self.daily_stats_key.format(date=today)
            
            pipe = self.redis_client.pipeline()
            
            # Daily counters
            pipe.hincrby(daily_key, "total", 1)
            pipe.hincrby(daily_key, f"thumbs_{feedback.feedback.value}", 1)
            pipe.hincrby(daily_key, f"language_{feedback.response_language}", 1)
            pipe.hincrby(daily_key, f"conversation_{feedback.conversation_type}", 1)
            
            # Global counters
            pipe.hincrby(self.global_stats_key, "total_feedback", 1)
            pipe.hincrby(self.global_stats_key, f"total_thumbs_{feedback.feedback.value}", 1)
            pipe.hincrby(self.global_stats_key, f"language_{feedback.response_language}", 1)
            pipe.hincrby(self.global_stats_key, f"conversation_{feedback.conversation_type}", 1)
            
            await pipe.execute()
            
        except Exception as e:
            logger.error(f"Failed to update stats: {e}")
    
    async def get_feedback_stats(self, days: int = 30) -> FeedbackStats:
        """Get comprehensive feedback statistics."""
        
        if not self.is_connected:
            await self.initialize()
        
        try:
            # Get global stats
            global_data = await self.redis_client.hgetall(self.global_stats_key)
            
            total_up = int(global_data.get("total_thumbs_up", 0))
            total_down = int(global_data.get("total_thumbs_down", 0))
            total_feedback = total_up + total_down
            
            # Calculate percentages
            up_percentage = (total_up / total_feedback * 100) if total_feedback > 0 else 0.0
            down_percentage = (total_down / total_feedback * 100) if total_feedback > 0 else 0.0
            
            # Get daily breakdown
            daily_stats = {}
            end_date = datetime.now()
            
            for i in range(days):
                date = end_date - timedelta(days=i)
                date_str = date.strftime("%Y-%m-%d")
                daily_key = self.daily_stats_key.format(date=date_str)
                
                daily_data = await self.redis_client.hgetall(daily_key)
                if daily_data:
                    daily_stats[date_str] = {
                        "up": int(daily_data.get("thumbs_up", 0)),
                        "down": int(daily_data.get("thumbs_down", 0)),
                        "total": int(daily_data.get("total", 0))
                    }
            
            # Get conversation type breakdown
            start_up = int(global_data.get("conversation_start", 0))
            start_down = int(global_data.get("conversation_start", 0))
            continue_up = int(global_data.get("conversation_continue", 0))
            continue_down = int(global_data.get("conversation_continue", 0))
            
            # Get language breakdown
            language_stats = {}
            for key, value in global_data.items():
                if key.startswith("language_"):
                    lang = key.replace("language_", "")
                    if lang not in language_stats:
                        language_stats[lang] = {"total": 0}
                    language_stats[lang]["total"] = int(value)
            
            return FeedbackStats(
                total_thumbs_up=total_up,
                total_thumbs_down=total_down,
                total_feedback=total_feedback,
                thumbs_up_percentage=round(up_percentage, 2),
                thumbs_down_percentage=round(down_percentage, 2),
                daily_stats=daily_stats,
                start_conversation_stats={"up": start_up, "down": start_down},
                continue_conversation_stats={"up": continue_up, "down": continue_down},
                language_stats=language_stats
            )
            
        except Exception as e:
            logger.error(f"Failed to get feedback stats: {e}")
            return FeedbackStats()
    
    async def get_response_feedback_count(self, response_id: str) -> Dict[str, int]:
        """Get feedback count for a specific response."""
        
        try:
            response_key = self.response_feedback_key.format(response_id=response_id)
            feedback_ids = await self.redis_client.lrange(response_key, 0, -1)
            
            up_count = 0
            down_count = 0
            
            for feedback_id in feedback_ids:
                feedback_key = self.feedback_key.format(feedback_id=feedback_id)
                feedback_data = await self.redis_client.get(feedback_key)
                
                if feedback_data:
                    feedback_json = json.loads(feedback_data)
                    if feedback_json.get("feedback") == "up":
                        up_count += 1
                    else:
                        down_count += 1
            
            return {
                "thumbs_up": up_count,
                "thumbs_down": down_count,
                "total": up_count + down_count
            }
            
        except Exception as e:
            logger.error(f"Failed to get response feedback count: {e}")
            return {"thumbs_up": 0, "thumbs_down": 0, "total": 0}
    
    async def get_feedback_export_data(self, days: int = None) -> Dict:
        """Export all feedback data for admin analysis."""
        
        try:
            # Get stats for the specified period
            if days:
                stats = await self.get_feedback_stats(days)
            else:
                stats = await self.get_all_time_stats()
            
            # Get all individual feedback records
            all_feedback = []
            
            feedback_pattern = self.feedback_key.format(feedback_id="*").replace("{feedback_id}", "*")
            feedback_keys = await self.redis_client.keys(feedback_pattern)
            
            logger.info(f"Exporting {len(feedback_keys)} feedback records")
            
            for key in feedback_keys:
                feedback_data = await self.redis_client.get(key)
                if feedback_data:
                    feedback_record = json.loads(feedback_data)
                    
                    # Filter by date if days is specified
                    if days:
                        feedback_date = datetime.fromisoformat(feedback_record['created_at'])
                        cutoff_date = datetime.now() - timedelta(days=days)
                        if feedback_date < cutoff_date:
                            continue
                    
                    all_feedback.append(feedback_record)
            
            # Sort by creation date
            all_feedback.sort(key=lambda x: x['created_at'])
            
            return {
                "export_date": datetime.now().isoformat(),
                "period_days": days if days else "all_time",
                "summary_statistics": stats.model_dump() if hasattr(stats, 'model_dump') else stats,
                "detailed_feedback": all_feedback,
                "total_records": len(all_feedback),
                "data_fields": [
                    "id", "response_id", "session_id", "feedback", 
                    "user_id", "created_at", "response_language", "conversation_type"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to export feedback data: {e}")
            return {"error": "Export failed", "details": str(e)}
    
    async def clear_all_feedback(self) -> bool:
        """Clear all feedback data (DANGEROUS - USE WITH CAUTION)."""
        
        if not self.is_connected:
            await self.initialize()
        
        try:
            logger.warning("ADMIN ACTION: Clearing ALL feedback data")
            
            # Get all feedback keys
            feedback_pattern = self.feedback_key.format(feedback_id="*").replace("{feedback_id}", "*")
            feedback_keys = await self.redis_client.keys(feedback_pattern)
            
            # Get all response feedback keys
            response_pattern = self.response_feedback_key.format(response_id="*").replace("{response_id}", "*")
            response_keys = await self.redis_client.keys(response_pattern)
            
            # Get all daily stats keys
            daily_pattern = self.daily_stats_key.format(date="*").replace("{date}", "*")
            daily_keys = await self.redis_client.keys(daily_pattern)
            
            # Get all session feedback keys
            session_pattern = self.session_feedback_key.format(session_id="*", response_id="*").replace("{session_id}", "*").replace("{response_id}", "*")
            session_keys = await self.redis_client.keys(session_pattern)
            
            # Collect all keys to delete
            all_keys = feedback_keys + response_keys + daily_keys + session_keys + [self.global_stats_key]
            
            # Delete all keys
            if all_keys:
                deleted_count = await self.redis_client.delete(*all_keys)
                logger.warning(f" Deleted {deleted_count} feedback-related keys")
            else:
                deleted_count = 0
                logger.info("No feedback data found to clear")
            
            logger.warning(f" Feedback data clearing completed. Deleted {deleted_count} records.")
            return True
            
        except Exception as e:
            logger.error(f" Failed to clear feedback data: {e}")
            return False
    
    async def export_research_data(self, days: int = None) -> Dict:
        """Export all feedback data for research analysis."""
        
        try:
            # Get stats for the specified period
            if days:
                stats = await self.get_feedback_stats(days)
            else:
                stats = await self.get_all_time_stats()
            
            # Get all feedback records
            all_feedback = []
            
            feedback_pattern = self.feedback_key.format(feedback_id="*").replace("{feedback_id}", "*")
            feedback_keys = await self.redis_client.keys(feedback_pattern)
            
            logger.info(f"Found {len(feedback_keys)} total feedback records")
            
            for key in feedback_keys:
                feedback_data = await self.redis_client.get(key)
                if feedback_data:
                    feedback_record = json.loads(feedback_data)
                    
                    # Filter by date if days is specified
                    if days:
                        feedback_date = datetime.fromisoformat(feedback_record['created_at'])
                        cutoff_date = datetime.now() - timedelta(days=days)
                        if feedback_date < cutoff_date:
                            continue
                    
                    all_feedback.append(feedback_record)
            
            # Sort by creation date
            all_feedback.sort(key=lambda x: x['created_at'])
            
            return {
                "export_date": datetime.now().isoformat(),
                "period_days": days if days else "all_time",
                "summary_statistics": stats.model_dump() if hasattr(stats, 'model_dump') else stats,
                "detailed_feedback": all_feedback,
                "total_records": len(all_feedback),
                "data_fields": [
                    "id", "response_id", "session_id", "feedback", 
                    "user_id", "created_at", "response_language", "conversation_type"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to export research data: {e}")
            return {"error": "Export failed"}
    
    async def get_all_time_stats(self) -> Dict:
        """Get complete statistics since data collection began."""
        
        try:
            daily_pattern = self.daily_stats_key.format(date="*").replace("{date}", "*")
            daily_keys = await self.redis_client.keys(daily_pattern)
            
            all_days_data = {}
            total_up = 0
            total_down = 0
            
            for key in daily_keys:
                date_str = key.split(":")[-1]
                daily_data = await self.redis_client.hgetall(key)
                
                if daily_data:
                    day_up = int(daily_data.get("thumbs_up", 0))
                    day_down = int(daily_data.get("thumbs_down", 0))
                    
                    all_days_data[date_str] = {
                        "up": day_up,
                        "down": day_down,
                        "total": day_up + day_down
                    }
                    
                    total_up += day_up
                    total_down += day_down
            
            total_feedback = total_up + total_down
            
            return {
                "all_time_total": total_feedback,
                "all_time_thumbs_up": total_up,
                "all_time_thumbs_down": total_down,
                "all_time_satisfaction_rate": round((total_up / total_feedback * 100), 2) if total_feedback > 0 else 0,
                "daily_breakdown": all_days_data,
                "collection_period": {
                    "start_date": min(all_days_data.keys()) if all_days_data else None,
                    "end_date": max(all_days_data.keys()) if all_days_data else None,
                    "total_days": len(all_days_data)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get all-time stats: {e}")
            return {}
    
    async def get_detailed_analytics(self) -> Dict:
        """Get detailed analytics for admin dashboard."""
        
        try:
            # Get basic stats
            stats = await self.get_feedback_stats(days=30)
            
            # Get additional metrics
            global_data = await self.redis_client.hgetall(self.global_stats_key)
            
            # Calculate engagement metrics
            total_feedback = stats.total_feedback
            
            # Get hourly distribution (simplified)
            hourly_stats = await self._get_hourly_distribution()
            
            # Get response time correlation (if available)
            response_time_correlation = await self._get_response_time_correlation()
            
            return {
                "basic_stats": stats.model_dump(),
                "engagement_metrics": {
                    "total_feedback": total_feedback,
                    "daily_average": total_feedback / 30 if total_feedback > 0 else 0,
                    "satisfaction_rate": stats.thumbs_up_percentage,
                    "engagement_trend": "positive" if stats.thumbs_up_percentage > 70 else "neutral"
                },
                "time_distribution": {
                    "hourly_stats": hourly_stats,
                    "peak_hours": self._find_peak_hours(hourly_stats)
                },
                "quality_metrics": {
                    "response_time_correlation": response_time_correlation,
                    "language_preference": self._get_language_preference(stats.language_stats)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get detailed analytics: {e}")
            return {"error": "Analytics unavailable"}
    
    async def _get_hourly_distribution(self) -> Dict[str, int]:
        """Get feedback distribution by hour of day."""
        
        try:
            hourly_counts = {}
            
            # Get all feedback records and analyze by hour
            feedback_pattern = self.feedback_key.format(feedback_id="*").replace("{feedback_id}", "*")
            feedback_keys = await self.redis_client.keys(feedback_pattern)
            
            for key in feedback_keys[:1000]:  # Limit to prevent performance issues
                feedback_data = await self.redis_client.get(key)
                if feedback_data:
                    feedback_record = json.loads(feedback_data)
                    created_at = datetime.fromisoformat(feedback_record['created_at'])
                    hour = created_at.hour
                    
                    hourly_counts[str(hour)] = hourly_counts.get(str(hour), 0) + 1
            
            return hourly_counts
            
        except Exception as e:
            logger.error(f"Failed to get hourly distribution: {e}")
            return {}
    
    async def _get_response_time_correlation(self) -> Dict[str, float]:
        """Get correlation between response time and feedback."""
        
        # This would require additional data collection
        # For now, return mock data
        return {
            "fast_responses_satisfaction": 85.2,
            "slow_responses_satisfaction": 72.1,
            "correlation_coefficient": -0.45
        }
    
    def _find_peak_hours(self, hourly_stats: Dict[str, int]) -> List[int]:
        """Find peak feedback hours."""
        
        if not hourly_stats:
            return []
        
        # Sort hours by feedback count
        sorted_hours = sorted(hourly_stats.items(), key=lambda x: x[1], reverse=True)
        
        # Return top 3 peak hours
        return [int(hour) for hour, count in sorted_hours[:3]]
    
    def _get_language_preference(self, language_stats: Dict) -> Dict[str, str]:
        """Get language preference insights."""
        
        if not language_stats:
            return {"primary": "en", "distribution": "uniform"}
        
        # Find most used language
        primary_lang = max(language_stats.items(), key=lambda x: x[1].get("total", 0))[0]
        
        total_feedback = sum(lang_data.get("total", 0) for lang_data in language_stats.values())
        primary_percentage = (language_stats[primary_lang].get("total", 0) / total_feedback * 100) if total_feedback > 0 else 0
        
        if primary_percentage > 80:
            distribution = "concentrated"
        elif primary_percentage > 50:
            distribution = "majority"
        else:
            distribution = "diverse"
        
        return {
            "primary": primary_lang,
            "distribution": distribution,
            "primary_percentage": round(primary_percentage, 1)
        }
    
    async def health_check(self) -> bool:
        """Check if service is working."""
        try:
            if not self.redis_client:
                return False
            await self.redis_client.ping()
            return True
        except Exception:
            return False


# Global feedback service
simple_feedback_service = SimpleFeedbackService()

async def get_simple_feedback_service() -> SimpleFeedbackService:
    """Get the feedback service instance."""
    if not simple_feedback_service.is_connected:
        await simple_feedback_service.initialize()
    return simple_feedback_service