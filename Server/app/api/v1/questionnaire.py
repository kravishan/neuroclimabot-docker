"""API endpoints for CHI 2027 research questionnaire with validated instruments."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime

from app.services.database.questionnaire_database import get_questionnaire_database
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class QuestionnaireRequestNew(BaseModel):
    """Request model for the new post-interaction questionnaire structure."""

    # Participant Information
    participant_id: Optional[str] = None
    email: Optional[EmailStr] = None

    # Demographics
    age_range: Optional[str] = None
    education_level: Optional[str] = None
    country: Optional[str] = None
    native_language: Optional[str] = None
    prior_climate_knowledge: Optional[str] = None
    prior_ai_experience: Optional[str] = None

    # Consent (single checkbox)
    consent_all: bool = Field(..., description="Single consent checkbox")

    # Section 1: Your Recent Experience
    primary_purpose: Optional[str] = None
    other_purpose: Optional[str] = None
    task_type: Optional[List[str]] = None

    # Section 2: Task Success & Completion
    task_success: Optional[Dict[str, Any]] = None
    info_finding: Optional[Dict[str, int]] = None

    # Section 3: Document & Source Quality
    doc_quality: Optional[Dict[str, int]] = None
    info_adequacy: Optional[Dict[str, str]] = None

    # Section 4: UEQ-S (8 items, 1-7 scale)
    ueq_s: Optional[Dict[str, int]] = None

    # Section 5: Trust Scale (12 items, 1-7 scale)
    trust_scale: Optional[Dict[str, int]] = None

    # Section 6: NASA-TLX (6 subscales, 0-20 scale)
    nasa_tlx: Optional[Dict[str, int]] = None

    # Section 7: Conversational Quality (5 items, 1-7 scale)
    conversational_quality: Optional[Dict[str, int]] = None

    # Section 8: Feature-Specific Evaluations
    stp_evaluation: Optional[Dict[str, int]] = None  # 4 items
    kg_visualization: Optional[Dict[str, int]] = None  # 5 items
    multilingual: Optional[Dict[str, int]] = None  # 3 items
    used_kg_viz: Optional[bool] = None
    used_non_english: Optional[bool] = None

    # Section 9: RAG Transparency & Behavioral Intentions
    rag_transparency: Optional[Dict[str, int]] = None  # 5 items
    behavioral_intentions: Optional[Dict[str, int]] = None  # 5 items

    # Section 10: Open-Ended Feedback
    most_useful_features: Optional[str] = None
    suggested_improvements: Optional[str] = None
    additional_comments: Optional[str] = None

    # Metadata
    submission_date: Optional[str] = None
    time_started: Optional[str] = None
    time_per_section: Optional[Dict[str, float]] = None
    total_time_seconds: Optional[float] = None


class QuestionnaireRequest(BaseModel):
    """Request model for CHI 2027 research questionnaire with validated instruments."""

    # Participant Information (Optional for anonymous participation)
    participant_id: Optional[str] = None
    email: Optional[EmailStr] = None
    submission_date: str = Field(..., description="Date of submission")
    native_language: Optional[str] = None
    country: Optional[str] = None

    # Demographics (Optional)
    age_range: Optional[str] = None
    education_level: Optional[str] = None
    field_of_study: Optional[str] = None
    prior_climate_knowledge_self_rated: Optional[int] = Field(None, ge=1, le=5)

    # Simplified Consent (Required)
    consent_agreed: bool = Field(..., description="Single consent checkbox")

    # MACK-12 Climate Knowledge Pre-Test (1-5 scale)
    mack_pre_1: Optional[int] = Field(None, ge=1, le=5)
    mack_pre_2: Optional[int] = Field(None, ge=1, le=5)
    mack_pre_3: Optional[int] = Field(None, ge=1, le=5)
    mack_pre_4: Optional[int] = Field(None, ge=1, le=5)
    mack_pre_5: Optional[int] = Field(None, ge=1, le=5)
    mack_pre_6: Optional[int] = Field(None, ge=1, le=5)
    mack_pre_7: Optional[int] = Field(None, ge=1, le=5)
    mack_pre_8: Optional[int] = Field(None, ge=1, le=5)
    mack_pre_9: Optional[int] = Field(None, ge=1, le=5)
    mack_pre_10: Optional[int] = Field(None, ge=1, le=5)
    mack_pre_11: Optional[int] = Field(None, ge=1, le=5)
    mack_pre_12: Optional[int] = Field(None, ge=1, le=5)

    # Prior AI Experience (1-7 Likert)
    prior_chatbot_usage: Optional[int] = Field(None, ge=1, le=7)
    prior_ai_familiarity: Optional[int] = Field(None, ge=1, le=7)
    prior_ai_trust_general: Optional[int] = Field(None, ge=1, le=7)

    # Task Completion Tracking
    tasks_completed: Optional[List[str]] = None
    task_1_query: Optional[str] = None
    task_2_query: Optional[str] = None
    task_3_query: Optional[str] = None
    task_4_query: Optional[str] = None
    task_5_query: Optional[str] = None

    # UEQ-S User Experience (8 items, 1-7 scale, semantic differential)
    ueq_1_obstructive_supportive: Optional[int] = Field(None, ge=1, le=7)
    ueq_2_complicated_easy: Optional[int] = Field(None, ge=1, le=7)
    ueq_3_inefficient_efficient: Optional[int] = Field(None, ge=1, le=7)
    ueq_4_confusing_clear: Optional[int] = Field(None, ge=1, le=7)
    ueq_5_boring_exciting: Optional[int] = Field(None, ge=1, le=7)
    ueq_6_not_interesting_interesting: Optional[int] = Field(None, ge=1, le=7)
    ueq_7_conventional_inventive: Optional[int] = Field(None, ge=1, le=7)
    ueq_8_usual_leading_edge: Optional[int] = Field(None, ge=1, le=7)

    # Human-AI Trust Scale (12 items, 1-7 Likert)
    trust_1_reliable_information: Optional[int] = Field(None, ge=1, le=7)
    trust_2_accurate_responses: Optional[int] = Field(None, ge=1, le=7)
    trust_3_trustworthy_system: Optional[int] = Field(None, ge=1, le=7)
    trust_4_confident_using: Optional[int] = Field(None, ge=1, le=7)
    trust_5_dependable: Optional[int] = Field(None, ge=1, le=7)
    trust_6_consistent_quality: Optional[int] = Field(None, ge=1, le=7)
    trust_7_comfortable_relying: Optional[int] = Field(None, ge=1, le=7)
    trust_8_positive_feelings: Optional[int] = Field(None, ge=1, le=7)
    trust_9_emotionally_trustworthy: Optional[int] = Field(None, ge=1, le=7)
    trust_10_sources_increase_trust: Optional[int] = Field(None, ge=1, le=7)
    trust_11_transparency_helpful: Optional[int] = Field(None, ge=1, le=7)
    trust_12_would_recommend: Optional[int] = Field(None, ge=1, le=7)

    # NASA-TLX Cognitive Load (6 subscales, 0-100 scale)
    nasa_mental_demand: Optional[int] = Field(None, ge=0, le=100)
    nasa_physical_demand: Optional[int] = Field(None, ge=0, le=100)
    nasa_temporal_demand: Optional[int] = Field(None, ge=0, le=100)
    nasa_performance: Optional[int] = Field(None, ge=0, le=100)
    nasa_effort: Optional[int] = Field(None, ge=0, le=100)
    nasa_frustration: Optional[int] = Field(None, ge=0, le=100)

    # RAG Transparency & Quality (5 items, 1-7 Likert)
    rag_source_relevance: Optional[int] = Field(None, ge=1, le=7)
    rag_citation_quality: Optional[int] = Field(None, ge=1, le=7)
    rag_verifiability: Optional[int] = Field(None, ge=1, le=7)
    rag_response_accuracy: Optional[int] = Field(None, ge=1, le=7)
    rag_limitation_clarity: Optional[int] = Field(None, ge=1, le=7)

    # Social Tipping Points Evaluation (if applicable, 1-7 Likert)
    stp_shown: Optional[bool] = False
    stp_understanding: Optional[int] = Field(None, ge=1, le=7)
    stp_clarity: Optional[int] = Field(None, ge=1, le=7)
    stp_influence: Optional[int] = Field(None, ge=1, le=7)

    # Knowledge Graph Evaluation (if applicable, 1-7 Likert)
    kg_used: Optional[bool] = False
    kg_understanding: Optional[int] = Field(None, ge=1, le=7)
    kg_navigation: Optional[int] = Field(None, ge=1, le=7)
    kg_task_success: Optional[bool] = None

    # Multilingual Experience (if non-English, 1-7 Likert)
    used_non_english: Optional[bool] = False
    ml_accuracy: Optional[int] = Field(None, ge=1, le=7)
    ml_preference: Optional[int] = Field(None, ge=1, le=7)

    # MACK-12 Climate Knowledge Post-Test (1-5 scale)
    mack_post_1: Optional[int] = Field(None, ge=1, le=5)
    mack_post_2: Optional[int] = Field(None, ge=1, le=5)
    mack_post_3: Optional[int] = Field(None, ge=1, le=5)
    mack_post_4: Optional[int] = Field(None, ge=1, le=5)
    mack_post_5: Optional[int] = Field(None, ge=1, le=5)
    mack_post_6: Optional[int] = Field(None, ge=1, le=5)
    mack_post_7: Optional[int] = Field(None, ge=1, le=5)
    mack_post_8: Optional[int] = Field(None, ge=1, le=5)
    mack_post_9: Optional[int] = Field(None, ge=1, le=5)
    mack_post_10: Optional[int] = Field(None, ge=1, le=5)
    mack_post_11: Optional[int] = Field(None, ge=1, le=5)
    mack_post_12: Optional[int] = Field(None, ge=1, le=5)

    # Behavioral Intentions (5 items, 1-7 Likert)
    behavior_1_change_behavior: Optional[int] = Field(None, ge=1, le=7)
    behavior_2_discuss_others: Optional[int] = Field(None, ge=1, le=7)
    behavior_3_seek_information: Optional[int] = Field(None, ge=1, le=7)
    behavior_4_support_policies: Optional[int] = Field(None, ge=1, le=7)
    behavior_5_take_action: Optional[int] = Field(None, ge=1, le=7)

    # Perceived Understanding (1-7 Likert)
    perceived_understanding: Optional[int] = Field(None, ge=1, le=7)

    # Open-Ended Feedback
    most_useful_features: Optional[str] = None
    suggested_improvements: Optional[str] = None
    additional_comments: Optional[str] = None

    # Metadata
    session_id: Optional[str] = None
    time_spent_seconds: Optional[int] = None
    device_type: Optional[str] = None


class QuestionnaireResponse(BaseModel):
    """Response model for questionnaire submission."""
    success: bool
    message: str
    questionnaire_id: Optional[int] = None


class QuestionnaireStats(BaseModel):
    """Statistics about questionnaire responses."""
    total_responses: int
    average_ueq_score: float
    average_trust_score: float
    average_nasa_tlx_score: float
    knowledge_gain: float


@router.post("/submit", response_model=QuestionnaireResponse)
async def submit_questionnaire(request: QuestionnaireRequestNew):
    """Submit CHI 2027 research questionnaire with new post-interaction structure."""

    try:
        # Validate consent
        if not request.consent_all:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Consent must be agreed to participate in the study"
            )

        # Get questionnaire database
        questionnaire_db = await get_questionnaire_database()

        # Prepare questionnaire data (convert Pydantic model to dict)
        questionnaire_data = request.dict()

        # Save to database
        questionnaire_id = await questionnaire_db.save_questionnaire(questionnaire_data)

        return QuestionnaireResponse(
            success=True,
            message="Thank you for participating in our research! Your response has been recorded.",
            questionnaire_id=questionnaire_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting questionnaire: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit questionnaire: {str(e)}"
        )


@router.get("/stats", response_model=QuestionnaireStats)
async def get_questionnaire_statistics():
    """Get statistics about questionnaire responses (admin endpoint)."""

    try:
        questionnaire_db = await get_questionnaire_database()
        responses = await questionnaire_db.get_questionnaires(limit=1000)

        if not responses:
            return QuestionnaireStats(
                total_responses=0,
                average_ueq_score=0.0,
                average_trust_score=0.0,
                average_nasa_tlx_score=0.0,
                knowledge_gain=0.0
            )

        # Calculate UEQ-S average (8 items, 1-7 scale)
        # Try both old and new format
        ueq_scores = []
        for r in responses:
            # New format (nested)
            if 'ueq_s' in r and isinstance(r['ueq_s'], dict):
                ueq_values = list(r['ueq_s'].values())
                valid_ueq = [score for score in ueq_values if isinstance(score, (int, float))]
                if valid_ueq:
                    ueq_scores.append(sum(valid_ueq) / len(valid_ueq))
            # Old format (flat)
            else:
                ueq_items = [
                    r.get('ueq_1_obstructive_supportive'), r.get('ueq_2_complicated_easy'),
                    r.get('ueq_3_inefficient_efficient'), r.get('ueq_4_confusing_clear'),
                    r.get('ueq_5_boring_exciting'), r.get('ueq_6_not_interesting_interesting'),
                    r.get('ueq_7_conventional_inventive'), r.get('ueq_8_usual_leading_edge')
                ]
                valid_ueq = [score for score in ueq_items if score is not None]
                if valid_ueq:
                    ueq_scores.append(sum(valid_ueq) / len(valid_ueq))

        # Calculate Trust average (12 items, 1-7 scale)
        trust_scores = []
        for r in responses:
            # New format (nested)
            if 'trust_scale' in r and isinstance(r['trust_scale'], dict):
                trust_values = list(r['trust_scale'].values())
                valid_trust = [score for score in trust_values if isinstance(score, (int, float))]
                if valid_trust:
                    trust_scores.append(sum(valid_trust) / len(valid_trust))
            # Old format (flat)
            else:
                trust_items = [
                    r.get('trust_1_reliable_information'), r.get('trust_2_accurate_responses'),
                    r.get('trust_3_trustworthy_system'), r.get('trust_4_confident_using'),
                    r.get('trust_5_dependable'), r.get('trust_6_consistent_quality'),
                    r.get('trust_7_comfortable_relying'), r.get('trust_8_positive_feelings'),
                    r.get('trust_9_emotionally_trustworthy'), r.get('trust_10_sources_increase_trust'),
                    r.get('trust_11_transparency_helpful'), r.get('trust_12_would_recommend')
                ]
                valid_trust = [score for score in trust_items if score is not None]
                if valid_trust:
                    trust_scores.append(sum(valid_trust) / len(valid_trust))

        # Calculate NASA-TLX average (6 subscales, 0-20 scale)
        nasa_scores = []
        for r in responses:
            # New format (nested)
            if 'nasa_tlx' in r and isinstance(r['nasa_tlx'], dict):
                nasa_values = list(r['nasa_tlx'].values())
                valid_nasa = [score for score in nasa_values if isinstance(score, (int, float))]
                if valid_nasa:
                    nasa_scores.append(sum(valid_nasa) / len(valid_nasa))
            # Old format (flat)
            else:
                nasa_items = [
                    r.get('nasa_mental_demand'), r.get('nasa_physical_demand'),
                    r.get('nasa_temporal_demand'), r.get('nasa_performance'),
                    r.get('nasa_effort'), r.get('nasa_frustration')
                ]
                valid_nasa = [score for score in nasa_items if score is not None]
                if valid_nasa:
                    nasa_scores.append(sum(valid_nasa) / len(valid_nasa))

        # Calculate MACK-12 knowledge gain (post - pre)
        knowledge_gains = []
        for r in responses:
            mack_pre = [
                r.get('mack_pre_1'), r.get('mack_pre_2'), r.get('mack_pre_3'), r.get('mack_pre_4'),
                r.get('mack_pre_5'), r.get('mack_pre_6'), r.get('mack_pre_7'), r.get('mack_pre_8'),
                r.get('mack_pre_9'), r.get('mack_pre_10'), r.get('mack_pre_11'), r.get('mack_pre_12')
            ]
            mack_post = [
                r.get('mack_post_1'), r.get('mack_post_2'), r.get('mack_post_3'), r.get('mack_post_4'),
                r.get('mack_post_5'), r.get('mack_post_6'), r.get('mack_post_7'), r.get('mack_post_8'),
                r.get('mack_post_9'), r.get('mack_post_10'), r.get('mack_post_11'), r.get('mack_post_12')
            ]
            valid_pre = [score for score in mack_pre if score is not None]
            valid_post = [score for score in mack_post if score is not None]
            if valid_pre and valid_post and len(valid_pre) == len(valid_post):
                pre_avg = sum(valid_pre) / len(valid_pre)
                post_avg = sum(valid_post) / len(valid_post)
                knowledge_gains.append(post_avg - pre_avg)

        return QuestionnaireStats(
            total_responses=len(responses),
            average_ueq_score=round(sum(ueq_scores) / len(ueq_scores), 2) if ueq_scores else 0.0,
            average_trust_score=round(sum(trust_scores) / len(trust_scores), 2) if trust_scores else 0.0,
            average_nasa_tlx_score=round(sum(nasa_scores) / len(nasa_scores), 2) if nasa_scores else 0.0,
            knowledge_gain=round(sum(knowledge_gains) / len(knowledge_gains), 2) if knowledge_gains else 0.0
        )

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
        questionnaire_db = await get_questionnaire_database()
        responses = await questionnaire_db.get_questionnaires(limit)

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
