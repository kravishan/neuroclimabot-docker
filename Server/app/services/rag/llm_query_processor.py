"""
Enhanced LLM Query Preprocessor with exact/fuzzy matching before LLM analysis
"""

import json
import re
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from difflib import SequenceMatcher

from app.config import get_settings
from app.services.llm.factory import get_llm
from app.services.prompts.manager import get_prompt_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class QueryCategory(Enum):
    """Query categories for routing."""
    CONVERSATIONAL = "conversational"
    BOT_IDENTITY = "bot_identity"
    CLIMATE_QUESTION = "climate_question"
    GENERAL_QUESTION = "general_question"
    UNCLEAR = "unclear"


@dataclass
class LLMQueryAnalysis:
    """Result of LLM query analysis - English only processing."""
    original_query: str
    category: QueryCategory
    confidence: float
    should_retrieve: bool
    suggested_response: Optional[str]
    enhanced_query: Optional[str]
    reasoning: str
    language_detected: str = "en"
    bot_identity_type: Optional[str] = None
    matched_from_json: bool = False


class CleanLLMQueryPreprocessor:
    """Clean LLM query preprocessor with JSON matching first, then LLM analysis"""
    
    def __init__(self):
        self.llm = None
        self.prompt_manager = None
        self.is_initialized = False
        
        # JSON data paths
        self.bot_identity_json_path = Path(__file__).parent.parent.parent / "templates" / "jsons" / "bot_identity_responses.json"
        self.conversational_json_path = Path(__file__).parent.parent.parent / "templates" / "jsons" / "conversational_samples.json"
        
        # Loaded JSON data
        self.bot_identity_data = None
        self.conversational_data = None
        
        # Statistics
        self.stats = {
            "total_queries": 0,
            "exact_json_matches": 0,
            "fuzzy_json_matches": 0,
            "llm_analysis_calls": 0,
            "conversational_queries": 0,
            "bot_identity_queries": 0,
            "climate_questions": 0,
            "general_questions": 0,
            "unclear_queries": 0,
            "start_basic_fixes": 0,
            "continue_full_processing": 0,
            "llm_generated_conversational": 0,
            "llm_generated_bot_identity": 0
        }
    
    async def initialize(self):
        """Initialize the LLM query preprocessor."""
        try:
            self.llm = await get_llm()
            self.prompt_manager = await get_prompt_manager()
            
            # Load JSON data
            self._load_json_data()
            
            self.is_initialized = True
            logger.info("✅ Clean LLM Query Preprocessor initialized with JSON matching")
        except Exception as e:
            logger.error(f"Failed to initialize LLM Query Preprocessor: {e}")
            raise
    
    def _load_json_data(self):
        """Load bot identity and conversational JSON files."""
        try:
            # Load bot identity responses
            if self.bot_identity_json_path.exists():
                with open(self.bot_identity_json_path, 'r', encoding='utf-8') as f:
                    self.bot_identity_data = json.load(f)
                logger.info(f"✅ Loaded bot identity responses from {self.bot_identity_json_path}")
            else:
                logger.warning(f"Bot identity JSON not found at {self.bot_identity_json_path}")
                self.bot_identity_data = {}
            
            # Load conversational samples
            if self.conversational_json_path.exists():
                with open(self.conversational_json_path, 'r', encoding='utf-8') as f:
                    self.conversational_data = json.load(f)
                logger.info(f"✅ Loaded conversational samples from {self.conversational_json_path}")
            else:
                logger.warning(f"Conversational JSON not found at {self.conversational_json_path}")
                self.conversational_data = {}
        
        except Exception as e:
            logger.error(f"Error loading JSON data: {e}")
            self.bot_identity_data = {}
            self.conversational_data = {}
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings using SequenceMatcher."""
        return SequenceMatcher(None, str1.lower().strip(), str2.lower().strip()).ratio()
    
    def _find_exact_or_fuzzy_match(self, query: str, json_data: Dict, threshold: float = 0.8) -> Optional[tuple]:
        """
        Find exact or fuzzy match in JSON data.
        Returns: (matched_pattern, response, similarity_score) or None
        """
        if not json_data:
            return None
        
        query_lower = query.lower().strip()
        best_match = None
        best_score = 0.0
        
        # Check all categories in JSON
        for category_name, category_data in json_data.items():
            # Handle nested structure (e.g., conversational_samples -> greetings -> samples)
            if isinstance(category_data, dict):
                # Check if this is a top-level category container (like "conversational_samples")
                if "samples" in category_data:
                    # Direct samples in category
                    samples = category_data["samples"]
                else:
                    # Nested categories (like greetings, farewells inside conversational_samples)
                    for subcategory_name, subcategory_data in category_data.items():
                        if isinstance(subcategory_data, dict) and "samples" in subcategory_data:
                            samples = subcategory_data["samples"]
                            
                            for sample in samples:
                                if isinstance(sample, dict):
                                    # Get patterns and response
                                    patterns = sample.get("patterns", [])
                                    response = sample.get("response", "")
                                    
                                    # Check each pattern
                                    for pattern in patterns:
                                        if isinstance(pattern, str):
                                            pattern_lower = pattern.lower().strip()
                                            
                                            # Exact match (highest priority)
                                            if pattern_lower == query_lower:
                                                logger.debug(f"✅ Exact match: '{pattern}' == '{query}'")
                                                return (pattern, response, 1.0)
                                            
                                            # Fuzzy match
                                            similarity = self._calculate_similarity(query, pattern)
                                            if similarity >= threshold and similarity > best_score:
                                                best_score = similarity
                                                best_match = (pattern, response, similarity)
                                                logger.debug(f"🔍 Fuzzy match candidate: '{pattern}' ~ '{query}' (score: {similarity:.2f})")
        
        if best_match:
            logger.debug(f"✅ Best fuzzy match: '{best_match[0]}' (score: {best_match[2]:.2f})")
        
        return best_match if best_score >= threshold else None
    
    async def analyze_query(
        self, 
        query: str, 
        conversation_context: Optional[str] = None,
        user_language: str = "en"
    ) -> LLMQueryAnalysis:
        """
        Analyze query with new flow:
        1. Check exact/fuzzy match in bot_identity_responses.json (>80%)
        2. Check exact/fuzzy match in conversational_samples.json (>80%)
        3. If no match, use LLM analysis
        """
        
        if not self.is_initialized:
            await self.initialize()
        
        self.stats["total_queries"] += 1
        
        try:
            # STEP 1: Check bot identity JSON for exact/fuzzy match
            bot_match = self._find_exact_or_fuzzy_match(query, self.bot_identity_data, threshold=0.8)
            
            if bot_match:
                matched_query, response, similarity = bot_match
                
                if similarity == 1.0:
                    self.stats["exact_json_matches"] += 1
                    logger.info(f"✅ Exact match found in bot_identity.json: '{matched_query}'")
                else:
                    self.stats["fuzzy_json_matches"] += 1
                    logger.info(f"✅ Fuzzy match found in bot_identity.json: '{matched_query}' (similarity: {similarity:.2f})")
                
                self.stats["bot_identity_queries"] += 1
                
                return LLMQueryAnalysis(
                    original_query=query,
                    category=QueryCategory.BOT_IDENTITY,
                    confidence=similarity,
                    should_retrieve=False,
                    suggested_response=response,
                    enhanced_query=None,
                    reasoning=f"Matched in bot_identity.json with {similarity:.2%} similarity",
                    language_detected="en",
                    bot_identity_type="matched_from_json",
                    matched_from_json=True
                )
            
            # STEP 2: Check conversational JSON for exact/fuzzy match
            conv_match = self._find_exact_or_fuzzy_match(query, self.conversational_data, threshold=0.8)
            
            if conv_match:
                matched_query, response, similarity = conv_match
                
                if similarity == 1.0:
                    self.stats["exact_json_matches"] += 1
                    logger.info(f"✅ Exact match found in conversational.json: '{matched_query}'")
                else:
                    self.stats["fuzzy_json_matches"] += 1
                    logger.info(f"✅ Fuzzy match found in conversational.json: '{matched_query}' (similarity: {similarity:.2f})")
                
                self.stats["conversational_queries"] += 1
                
                return LLMQueryAnalysis(
                    original_query=query,
                    category=QueryCategory.CONVERSATIONAL,
                    confidence=similarity,
                    should_retrieve=False,
                    suggested_response=response,
                    enhanced_query=None,
                    reasoning=f"Matched in conversational.json with {similarity:.2%} similarity",
                    language_detected="en",
                    matched_from_json=True
                )
            
            # STEP 3: No JSON match found - Use LLM analysis
            logger.info(f"🔍 No JSON match found for '{query}' - using LLM analysis")
            self.stats["llm_analysis_calls"] += 1
            
            analysis_prompt = self._create_enhanced_analysis_prompt(
                query=query,
                conversation_context=conversation_context
            )
            
            llm_response = await self._call_llm(analysis_prompt)
            analysis = self._parse_llm_analysis(llm_response, query, conversation_context)
            
            # If LLM says conversational, generate response using LLM
            if analysis.category == QueryCategory.CONVERSATIONAL:
                self.stats["conversational_queries"] += 1
                self.stats["llm_generated_conversational"] += 1
                
                suggested_response = await self._generate_conversational_response(
                    query, conversation_context
                )
                
                analysis.suggested_response = suggested_response
                analysis.reasoning += " | Response generated by LLM"
            
            # If LLM says bot_identity, generate response using LLM + bot_identity.json data
            elif analysis.category == QueryCategory.BOT_IDENTITY:
                self.stats["bot_identity_queries"] += 1
                self.stats["llm_generated_bot_identity"] += 1
                
                suggested_response = await self._generate_bot_identity_response_with_llm(
                    query, self.bot_identity_data
                )
                
                analysis.suggested_response = suggested_response
                analysis.reasoning += " | Response generated by LLM using bot_identity.json context"
            
            # Update stats for other categories
            elif analysis.category == QueryCategory.CLIMATE_QUESTION:
                self.stats["climate_questions"] += 1
            elif analysis.category == QueryCategory.GENERAL_QUESTION:
                self.stats["general_questions"] += 1
            elif analysis.category == QueryCategory.UNCLEAR:
                self.stats["unclear_queries"] += 1
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in query analysis: {e}")
            return self._create_fallback_analysis(query)
    
    def _create_enhanced_analysis_prompt(
        self, query: str, conversation_context: Optional[str]
    ) -> str:
        """Create enhanced analysis prompt using existing template method - English only."""
        
        return self.prompt_manager.render_query_analysis_prompt(
            query=query,
            language="en",
            conversation_context=conversation_context
        )
    
    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt."""
        if hasattr(self.llm, '_acall'):
            return await self.llm._acall(prompt)
        else:
            import asyncio
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.llm, prompt)
    
    def _parse_llm_analysis(
        self, llm_response: str, original_query: str, 
        conversation_context: Optional[str]
    ) -> LLMQueryAnalysis:
        """Parse LLM response into structured analysis - English only."""
        
        try:
            json_text = self._extract_json_from_response(llm_response)
            
            if json_text:
                data = json.loads(json_text)
                
                category = self._parse_category(data.get("category", "unclear"))
                confidence = max(0.0, min(1.0, float(data.get("confidence", 0.5))))
                should_retrieve = bool(data.get("should_retrieve", True))
                
                # Override should_retrieve for conversational and bot_identity
                if category == QueryCategory.CONVERSATIONAL or category == QueryCategory.BOT_IDENTITY:
                    should_retrieve = False
                elif category in [QueryCategory.CLIMATE_QUESTION, QueryCategory.GENERAL_QUESTION, QueryCategory.UNCLEAR]:
                    should_retrieve = True
                
                return LLMQueryAnalysis(
                    original_query=original_query,
                    category=category,
                    confidence=confidence,
                    should_retrieve=should_retrieve,
                    suggested_response=None,  # Will be generated separately
                    enhanced_query=data.get("enhanced_query"),
                    reasoning=data.get("reasoning", "LLM analysis completed"),
                    language_detected="en",
                    matched_from_json=False
                )
            
        except Exception as e:
            logger.warning(f"Error parsing LLM analysis: {e}")
        
        return self._create_fallback_analysis(original_query)
    
    def _extract_json_from_response(self, response: str) -> Optional[str]:
        """Extract JSON from LLM response."""
        
        patterns = [
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',
            r'```json\s*(\{.*?\})\s*```',
            r'```\s*(\{.*?\})\s*```'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
            if matches:
                return matches[0] if isinstance(matches[0], str) else matches[0]
        
        # Manual brace matching as fallback
        start = response.find('{')
        if start != -1:
            brace_count = 0
            for i, char in enumerate(response[start:], start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return response[start:i+1]
        
        return None
    
    def _parse_category(self, category_str: str) -> QueryCategory:
        """Parse category string to enum."""
        category_map = {
            "conversational": QueryCategory.CONVERSATIONAL,
            "bot_identity": QueryCategory.BOT_IDENTITY,
            "climate_question": QueryCategory.CLIMATE_QUESTION,
            "general_question": QueryCategory.GENERAL_QUESTION,
            "unclear": QueryCategory.UNCLEAR
        }
        return category_map.get(category_str.lower(), QueryCategory.UNCLEAR)
    
    async def _generate_conversational_response(
        self, query: str, conversation_context: Optional[str]
    ) -> str:
        """Generate conversational response using LLM - English only."""
        
        try:
            prompt = self.prompt_manager.render_conversational_response_prompt(
                query=query,
                conversation_context=conversation_context,
                language="en"
            )
            
            response = await self._call_llm(prompt)
            return response.strip().strip('"')
            
        except Exception as e:
            logger.error(f"Error generating conversational response: {e}")
            return self._get_simple_conversational_response(query)
    
    async def _generate_bot_identity_response_with_llm(
        self, query: str, bot_identity_data: Dict
    ) -> str:
        """Generate bot identity response using LLM with full bot_identity.json context."""
        
        try:
            # Convert bot_identity_data to readable context string
            bot_context = self._format_bot_identity_context(bot_identity_data)
            
            prompt = self.prompt_manager.render_bot_identity_prompt(
                query=query,
                language="en",
                query_type="general_identity"
            )
            
            # Add bot identity context to the prompt
            full_prompt = f"{prompt}\n\nBOT IDENTITY KNOWLEDGE BASE:\n{bot_context}"
            
            response = await self._call_llm(full_prompt)
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error generating bot identity response with LLM: {e}")
            return "Hello! I'm NeuroClima Bot, an AI assistant specialized in climate change and environmental policy. How can I help you today?"
    
    def _format_bot_identity_context(self, bot_identity_data: Dict) -> str:
        """Format bot identity JSON data into readable context for LLM."""
        
        context_parts = []
        
        for category_name, category_data in bot_identity_data.items():
            if isinstance(category_data, dict):
                # Add category description if available
                if "description" in category_data:
                    context_parts.append(f"\n{category_name.upper()}:")
                    context_parts.append(category_data["description"])
                
                # Add samples
                if "samples" in category_data:
                    for sample in category_data["samples"]:
                        if isinstance(sample, dict) and "response" in sample:
                            context_parts.append(f"- {sample['response']}")
        
        return "\n".join(context_parts)
    
    def _get_simple_conversational_response(self, query: str) -> str:
        """Get simple conversational response as fallback - English only."""
        
        query_lower = query.lower().strip()
        
        if any(greeting in query_lower for greeting in ["hi", "hello", "hey"]):
            return "Hello! I'm NeuroClima Bot, your AI assistant for climate and environmental topics. How can I help you today?"
        elif any(thanks in query_lower for thanks in ["thank", "thanks"]):
            return "You're welcome! I'm here to help with climate and environmental questions."
        elif "how are you" in query_lower:
            return "I'm doing great, thank you! Ready to help with any climate questions you might have."
        elif any(bye in query_lower for bye in ["bye", "goodbye"]):
            return "Goodbye! Feel free to return anytime with climate questions!"
        else:
            return "That's interesting! I'm NeuroClima Bot, here to help with climate and environmental topics. What would you like to explore?"
    
    def _create_fallback_analysis(self, query: str) -> LLMQueryAnalysis:
        """Create fallback analysis when LLM parsing fails - English only."""
        
        query_lower = query.lower().strip()
        
        # Check for climate keywords
        climate_keywords = [
            'climate', 'warming', 'carbon', 'emission', 'greenhouse',
            'renewable', 'environment', 'sustainability', 'pollution',
            'temperature', 'weather', 'energy', 'fossil', 'green'
        ]
        
        if any(keyword in query_lower for keyword in climate_keywords):
            category = QueryCategory.CLIMATE_QUESTION
        else:
            category = QueryCategory.GENERAL_QUESTION
        
        return LLMQueryAnalysis(
            original_query=query,
            category=category,
            confidence=0.5,
            should_retrieve=True,
            suggested_response=None,
            enhanced_query=None,
            reasoning="Fallback: Rule-based classification",
            language_detected="en",
            matched_from_json=False
        )
    
    async def apply_basic_fixes_for_start(
        self, query: str, language: str = "en"
    ) -> str:
        """Apply only basic grammar and spelling fixes for start conversations using LLM - English only."""
        
        if not self.is_initialized:
            await self.initialize()
        
        try:
            self.stats["start_basic_fixes"] += 1
            
            prompt = self.prompt_manager.render_query_enhancement_start_prompt(
                query=query,
                language="en",
                conversation_context=None
            )
            
            enhanced_query = await self._call_llm(prompt)
            processed_query = enhanced_query.strip().strip('"\'')
            
            if processed_query == query:
                logger.debug(f"Start query needs no fixes: {query}")
                return query
            
            logger.debug(f"Start query fixed: '{query}' -> '{processed_query}'")
            return processed_query
            
        except Exception as e:
            logger.error(f"Error in LLM basic fixes for start conversation: {e}")
            return query
    
    async def apply_full_processing_for_continue(
        self, query: str, language: str = "en", conversation_context: Optional[str] = None
    ) -> str:
        """Apply full processing (grammar + spelling + pronoun resolution) for continue conversations - English only."""
        
        if not self.is_initialized:
            await self.initialize()
        
        try:
            self.stats["continue_full_processing"] += 1
            
            prompt = self.prompt_manager.render_query_enhancement_continue_prompt(
                query=query,
                language="en",
                conversation_context=conversation_context
            )
            
            enhanced_query = await self._call_llm(prompt)
            processed_query = enhanced_query.strip().strip('"\'')
            
            logger.debug(f"Continue query processed: '{query}' -> '{processed_query}'")
            return processed_query
            
        except Exception as e:
            logger.error(f"Error in full processing for continue conversation: {e}")
            return query
    
    def get_stats(self) -> Dict[str, any]:
        """Get preprocessing statistics."""
        total = self.stats["total_queries"]
        return {
            **self.stats,
            "exact_json_match_rate": self.stats["exact_json_matches"] / total if total > 0 else 0,
            "fuzzy_json_match_rate": self.stats["fuzzy_json_matches"] / total if total > 0 else 0,
            "llm_analysis_rate": self.stats["llm_analysis_calls"] / total if total > 0 else 0,
            "conversational_rate": self.stats["conversational_queries"] / total if total > 0 else 0,
            "bot_identity_rate": self.stats["bot_identity_queries"] / total if total > 0 else 0,
            "climate_question_rate": self.stats["climate_questions"] / total if total > 0 else 0,
            "general_question_rate": self.stats["general_questions"] / total if total > 0 else 0,
            "llm_generated_conversational_rate": self.stats["llm_generated_conversational"] / total if total > 0 else 0,
            "llm_generated_bot_identity_rate": self.stats["llm_generated_bot_identity"] / total if total > 0 else 0,
            "processing_language": "english_only",
            "json_matching_enabled": True
        }
    
    async def health_check(self) -> bool:
        """Health check."""
        try:
            if not self.is_initialized:
                return False
            
            # Check if JSON data is loaded
            json_loaded = (self.bot_identity_data is not None and 
                          self.conversational_data is not None)
            
            # Test analysis
            test_analysis = await self.analyze_query("Hello")
            analysis_ok = (test_analysis.category == QueryCategory.CONVERSATIONAL and 
                          bool(test_analysis.suggested_response))
            
            return json_loaded and analysis_ok
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# Global instance
clean_llm_query_preprocessor = CleanLLMQueryPreprocessor()


async def get_llm_query_preprocessor() -> CleanLLMQueryPreprocessor:
    """Get the clean LLM query preprocessor instance."""
    if not clean_llm_query_preprocessor.is_initialized:
        await clean_llm_query_preprocessor.initialize()
    return clean_llm_query_preprocessor