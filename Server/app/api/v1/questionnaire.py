"""API endpoints for research questionnaire submission and retrieval."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime

from app.services.database.stats_database import get_stats_database
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class QuestionnaireRequest(BaseModel):
    """Request model for submitting research questionnaire."""

    # Participant Information
    first_name: str = Field(..., min_length=1, description="Participant's first name")
    last_name: str = Field(..., min_length=1, description="Participant's last name")
    email: EmailStr = Field(..., description="Participant's email address")
    submission_date: str = Field(..., description="Date of submission (MM/DD/YYYY)")

    # Informed Consent (all required)
    consent_study_info: bool = Field(..., description="Consent to study information")
    consent_age_18: bool = Field(..., description="Confirmation of age 18+")
    consent_voluntary: bool = Field(..., description="Voluntary participation consent")
    consent_data_collection: bool = Field(..., description="Consent for data collection")
    consent_privacy_notice: bool = Field(..., description="Acknowledged privacy notice")
    consent_data_processing: bool = Field(..., description="Consent for data processing")
    consent_publications: bool = Field(..., description="Consent for use in publications")
    consent_anonymity: bool = Field(..., description="Understanding of anonymity")
    consent_open_science: bool = Field(..., description="Consent for Open Science Foundation deposit")

    # User Experience
    overall_experience_rating: Optional[int] = Field(None, ge=1, le=5, description="Overall experience rating (1-5)")
    information_accuracy: Optional[str] = Field(None, description="Agreement scale for information accuracy")
    understanding_improvement: Optional[str] = Field(None, description="Agreement scale for understanding improvement")
    response_clarity: Optional[str] = Field(None, description="Agreement scale for response clarity")
    response_time_satisfaction: Optional[str] = Field(None, description="Agreement scale for response time")

    # Content & Usability
    topics_discussed: Optional[List[str]] = Field(default=[], description="Topics discussed with the bot")
    used_voice_feature: bool = Field(default=False, description="Whether voice feature was used")
    voice_experience_rating: Optional[int] = Field(None, ge=1, le=5, description="Voice experience rating (1-5)")
    most_useful_features: Optional[str] = Field(None, description="Most useful features feedback")
    suggested_improvements: Optional[str] = Field(None, description="Suggested improvements")

    # Demographics (optional)
    age_range: Optional[str] = Field(None, description="Age range")
    education_level: Optional[str] = Field(None, description="Education level")
    field_of_study: Optional[str] = Field(None, description="Field of study or work")
    prior_climate_knowledge: Optional[str] = Field(None, description="Prior knowledge of climate change")

    # Metadata
    session_id: Optional[str] = Field(None, description="Session ID if available")


class QuestionnaireResponse(BaseModel):
    """Response model for questionnaire submission."""
    success: bool
    message: str
    questionnaire_id: Optional[int] = None


class QuestionnaireStats(BaseModel):
    """Statistics about questionnaire responses."""
    total_responses: int
    average_experience_rating: float
    voice_feature_users: int
    voice_usage_percentage: float


@router.post("/submit", response_model=QuestionnaireResponse)
async def submit_questionnaire(request: QuestionnaireRequest):
    """Submit a research questionnaire response."""

    try:
        # Validate all consent fields are True
        consent_fields = [
            request.consent_study_info,
            request.consent_age_18,
            request.consent_voluntary,
            request.consent_data_collection,
            request.consent_privacy_notice,
            request.consent_data_processing,
            request.consent_publications,
            request.consent_anonymity,
            request.consent_open_science
        ]

        if not all(consent_fields):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All consent fields must be accepted to participate in the study"
            )

        # Get stats database
        stats_db = await get_stats_database()

        # Prepare questionnaire data
        questionnaire_data = {
            'first_name': request.first_name,
            'last_name': request.last_name,
            'email': request.email,
            'submission_date': request.submission_date,
            'consent_study_info': 1 if request.consent_study_info else 0,
            'consent_age_18': 1 if request.consent_age_18 else 0,
            'consent_voluntary': 1 if request.consent_voluntary else 0,
            'consent_data_collection': 1 if request.consent_data_collection else 0,
            'consent_privacy_notice': 1 if request.consent_privacy_notice else 0,
            'consent_data_processing': 1 if request.consent_data_processing else 0,
            'consent_publications': 1 if request.consent_publications else 0,
            'consent_anonymity': 1 if request.consent_anonymity else 0,
            'consent_open_science': 1 if request.consent_open_science else 0,
            'overall_experience_rating': request.overall_experience_rating,
            'information_accuracy': request.information_accuracy,
            'understanding_improvement': request.understanding_improvement,
            'response_clarity': request.response_clarity,
            'response_time_satisfaction': request.response_time_satisfaction,
            'topics_discussed': request.topics_discussed,
            'used_voice_feature': 1 if request.used_voice_feature else 0,
            'voice_experience_rating': request.voice_experience_rating,
            'most_useful_features': request.most_useful_features,
            'suggested_improvements': request.suggested_improvements,
            'age_range': request.age_range,
            'education_level': request.education_level,
            'field_of_study': request.field_of_study,
            'prior_climate_knowledge': request.prior_climate_knowledge,
            'session_id': request.session_id
        }

        # Save to database
        questionnaire_id = await stats_db.save_research_questionnaire(questionnaire_data)

        return QuestionnaireResponse(
            success=True,
            message="Thank you for completing the research questionnaire! Your response has been recorded.",
            questionnaire_id=questionnaire_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting questionnaire: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit questionnaire"
        )


@router.get("/stats", response_model=QuestionnaireStats)
async def get_questionnaire_statistics():
    """Get statistics about questionnaire responses (admin endpoint)."""

    try:
        # Get stats database
        stats_db = await get_stats_database()

        # Get questionnaire stats
        stats = await stats_db.get_questionnaire_stats()

        return QuestionnaireStats(**stats)

    except Exception as e:
        logger.error(f"Error getting questionnaire statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get questionnaire statistics"
        )


@router.get("/responses")
async def get_questionnaire_responses(limit: int = 100):
    """Get all questionnaire responses (admin endpoint)."""

    try:
        # Get stats database
        stats_db = await get_stats_database()

        # Get questionnaire responses
        responses = await stats_db.get_research_questionnaires(limit)

        return {
            "success": True,
            "count": len(responses),
            "responses": responses
        }

    except Exception as e:
        logger.error(f"Error getting questionnaire responses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get questionnaire responses"
        )
