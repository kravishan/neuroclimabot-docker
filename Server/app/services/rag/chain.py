import asyncio
import re
import time
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.core.exceptions import RAGException
from app.services.rag.orchestrator import get_rag_orchestrator
from app.services.memory.conversation import get_conversation_memory
from app.services.external.stp_client import get_stp_client
from app.services.tracing import get_langfuse_client, is_langfuse_enabled
from app.services.tracing import is_trulens_enabled, queue_rag_evaluation
from app.utils.references import process_references_with_urls_and_count
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class CleanRAGService:
    """Clean RAG service with STP integration - Pure English processing with response-based STP"""
    
    def __init__(self):
        self.orchestrator = None
        self.prompt_manager = None
        self.stp_client = None
        self.is_initialized = False
        
        # Performance tracking
        self.performance_stats = {
            "total_queries": 0,
            "conversational_queries": 0,
            "bot_identity_queries": 0,
            "substantive_queries": 0,
            "rag_responses": 0,
            "avg_response_time": 0.0,
            "avg_retrieval_time": 0.0,
            "avg_llm_time": 0.0,
            "cache_hits": 0,
            "error_count": 0,
            "start_basic_fixes": 0,
            "continue_full_processing": 0,
            "stp_requests": 0,
            "stp_success_count": 0,
            "stp_from_response": 0,
            "fallback_responses": 0,
            "parsing_failures": 0
        }
    
    async def initialize(self):
        """Initialize the RAG service with STP integration"""
        try:
            from app.services.prompts.manager import get_prompt_manager
            
            self.orchestrator, self.prompt_manager, self.stp_client = await asyncio.gather(
                get_rag_orchestrator(),
                get_prompt_manager(),
                self._get_stp_client_async()
            )
            
            self.is_initialized = True
            logger.info("✅ Clean RAG service initialized with response-based STP integration")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {e}")
            raise RAGException(f"RAG service initialization failed: {str(e)}")
    
    async def _get_stp_client_async(self):
        """Get STP client asynchronously."""
        return get_stp_client()
    
    async def query(
        self,
        question: str,
        session_id: Optional[str] = None,
        include_sources: bool = True,
        language: str = "en",
        difficulty_level: str = "low",
        conversation_type: str = "continue",
        **kwargs
    ) -> Dict[str, Any]:
        """Process a query with STP integration """
        
        if not self.is_initialized:
            await self.initialize()
        
        total_start_time = time.perf_counter()
        retrieval_time = 0.0
        llm_time = 0.0
        
        # Update performance stats
        self.performance_stats["total_queries"] += 1
        
        try:            
            # Analyze English query with conversation type awareness
            query_analysis = None
            analysis_start = time.perf_counter()
            
            if is_langfuse_enabled():
                langfuse_client = get_langfuse_client()
                with langfuse_client.start_as_current_span(
                    name="query_preprocessing",
                    input=question,
                    metadata={
                        "component": "llm_query_processor", 
                        "step": "0_analysis", 
                        "language": "en",
                        "conversation_type": conversation_type
                    }
                ) as span:
                    query_analysis = await self._analyze_query(
                        question, session_id, "en", conversation_type
                    )
                    span.update(
                        output=f"Category: {query_analysis.category.value}, Should retrieve: {query_analysis.should_retrieve}",
                        metadata={
                            "category": query_analysis.category.value,
                            "should_retrieve": query_analysis.should_retrieve,
                            "confidence": query_analysis.confidence,
                            "bot_identity_type": query_analysis.bot_identity_type,
                            "conversation_type": conversation_type
                        }
                    )
            else:
                query_analysis = await self._analyze_query(
                    question, session_id, "en", conversation_type
                )
            
            analysis_time = time.perf_counter() - analysis_start
            
            # Route based on analysis
            if query_analysis.category.value == "bot_identity":
                # Bot identity query - direct response (no STP needed)
                self.performance_stats["bot_identity_queries"] += 1
                self.performance_stats["rag_responses"] += 1
                llm_start = time.perf_counter()
                result = await self._handle_bot_identity_query(query_analysis)
                llm_time = time.perf_counter() - llm_start
                
            elif not query_analysis.should_retrieve:
                # Conversational query - no retrieval (no STP needed)
                self.performance_stats["conversational_queries"] += 1
                self.performance_stats["rag_responses"] += 1
                llm_start = time.perf_counter()
                result = await self._handle_conversational_query(query_analysis)
                llm_time = time.perf_counter() - llm_start
                
            else:
                # Substantive query - use knowledge base WITH response-based STP integration
                self.performance_stats["substantive_queries"] += 1
                
                # Track detailed timing for substantive queries with response-based STP
                substantive_start = time.perf_counter()
                result = await self._handle_substantive_query_with_response_stp(
                    query_analysis, session_id, difficulty_level, 
                    include_sources, conversation_type
                )
                
                # Extract timing information from the result if available
                total_substantive_time = time.perf_counter() - substantive_start
                
                # Estimate breakdown
                retrieval_time = total_substantive_time * 0.35
                llm_time = total_substantive_time * 0.5  # LLM time
            
            # Calculate total time
            total_time = time.perf_counter() - total_start_time

            # Update internal performance stats
            self._update_performance_stats(total_time, retrieval_time, llm_time)
            
            logger.info(f"English query with response-based STP processed successfully in {total_time:.3f}s")
            
            return result
                
        except Exception as e:
            self.performance_stats["error_count"] += 1
            logger.error(f"Query processing failed: {e}")
            
            # Add error span
            if is_langfuse_enabled():
                langfuse_client = get_langfuse_client()
                with langfuse_client.start_as_current_span(
                    name="query_error",
                    input=f"Error processing: {question}",
                    metadata={"component": "rag_service", "step": "error"}
                ) as span:
                    span.update(
                        output=f"Query processing failed: {str(e)}",
                        level="ERROR",
                        metadata={"error_message": str(e)}
                    )
            
            return await self._generate_error_response(question, str(e))
    
    async def _handle_bot_identity_query(self, query_analysis) -> Dict[str, Any]:
        """Handle bot identity queries with LLM-generated response."""
        
        response_content = query_analysis.suggested_response or self._get_default_bot_response()
        
        if is_langfuse_enabled():
            langfuse_client = get_langfuse_client()
            with langfuse_client.start_as_current_span(
                name="bot_identity_response",
                input=query_analysis.original_query,
                metadata={
                    "component": "bot_identity_handler", 
                    "step": "llm_generated_response",
                    "bot_identity_type": query_analysis.bot_identity_type,
                    "language": "en"
                }
            ) as span:
                span.update(
                    output=response_content[:200],
                    metadata={
                        "response_type": "bot_identity",
                        "category": query_analysis.category.value,
                        "identity_type": query_analysis.bot_identity_type,
                        "llm_generated": True
                    }
                )
        
        return {
            "answer": response_content,
            "title": "NeuroClima Bot Information",
            "social_tipping_point": "",
            "sources": [],
            "total_references": 0
        }
    
    def _get_default_bot_response(self) -> str:
        """Get default bot identity response as fallback."""
        return "Hello! I'm NeuroClima Bot, an AI assistant specialized in climate change and environmental policy, with a particular focus on EU climate policies and regulations. I was developed by the Future Computing Group at the University of Oulu, Finland, as part of a research project funded by the European Union. How can I help you with climate topics today?"
    
    async def _handle_conversational_query(self, query_analysis) -> Dict[str, Any]:
        """Handle conversational queries"""
        response_content = query_analysis.suggested_response or self._get_default_greeting()
        
        if is_langfuse_enabled():
            langfuse_client = get_langfuse_client()
            with langfuse_client.start_as_current_span(
                name="conversational_response",
                input=query_analysis.original_query,
                metadata={"component": "conversational_handler", "step": "direct_response", "language": "en"}
            ) as span:
                span.update(
                    output=response_content[:200],
                    metadata={
                        "response_type": "conversational",
                        "category": query_analysis.category.value
                    }
                )
        
        return {
            "answer": response_content,
            "title": "NeuroClima Bot",
            "social_tipping_point": "",
            "sources": [],
            "total_references": 0
        }
    
    async def _handle_substantive_query_with_response_stp(
        self, query_analysis, session_id: Optional[str], 
        difficulty_level: str, include_sources: bool, conversation_type: str
    ) -> Dict[str, Any]:
        """Handle substantive queries with response-based STP processing"""
        
        # Apply simplified query processing based on conversation type
        processed_query = None
        was_processed = False
        
        if conversation_type == "start":
            # Start conversation: only basic fixes
            from app.services.rag.llm_query_processor import get_llm_query_preprocessor
            preprocessor = await get_llm_query_preprocessor()
            processed_query = await preprocessor.apply_basic_fixes_for_start(
                query_analysis.original_query, "en"
            )
            was_processed = (processed_query != query_analysis.original_query)
            
            if was_processed:
                self.performance_stats["start_basic_fixes"] += 1
                logger.debug(f"Start query basic fixes: '{query_analysis.original_query}' -> '{processed_query}'")
        else:
            # Continue conversation: full processing with pronoun resolution
            from app.services.rag.llm_query_processor import get_llm_query_preprocessor
            preprocessor = await get_llm_query_preprocessor()
            conversation_context = await self._get_conversation_context(session_id) if session_id else None
            
            processed_query = await preprocessor.apply_full_processing_for_continue(
                query_analysis.original_query, "en", conversation_context
            )
            was_processed = (processed_query != query_analysis.original_query)
            
            if was_processed:
                self.performance_stats["continue_full_processing"] += 1
                logger.debug(f"Continue query full processing: '{query_analysis.original_query}' -> '{processed_query}'")
        
        # Get RAG result using the appropriate orchestrator method
        if conversation_type == "start":
            rag_result = await self.orchestrator.process_start_conversation(
                original_query=query_analysis.original_query,
                processed_query=processed_query if was_processed else None,
                language="en",
                difficulty_level=difficulty_level,
                was_processed=was_processed
            )
        else:
            conversation_memory = await self._get_conversation_memory(session_id) if session_id else ""
            rag_result = await self.orchestrator.process_continue_conversation(
                original_query=query_analysis.original_query,
                conversation_memory=conversation_memory,
                processed_query=processed_query if was_processed else None,
                language="en",
                difficulty_level=difficulty_level,
                was_processed=was_processed,
                message_count=1
            )
        
        has_relevant_data = self._check_has_relevant_data(rag_result)
        
        if has_relevant_data:
            # Normal RAG response - first get the response content, then find STP from it
            self.performance_stats["rag_responses"] += 1
            
            # Get the English response content
            english_response = rag_result.content
            
            # Process sources if needed
            sources_result = {"sources": [], "total_references": 0}
            if include_sources:
                try:
                    sources_result = await self._generate_sources(rag_result.reference_data)
                except Exception as e:
                    logger.error(f"Source processing failed: {e}")
            
            # NOW get STP based on the LLM response content
            logger.info(f"🔍 Retrieving STP based on LLM response (first 200 chars): {english_response[:200]}...")
            social_tipping_point = await self._get_stp_from_response(english_response)
            
            result = {
                "answer": english_response,
                "title": rag_result.title,
                "social_tipping_point": social_tipping_point,
                "sources": sources_result["sources"],
                "total_references": sources_result["total_references"]
            }

            # Queue TruLens evaluation (async, non-blocking, zero latency impact)
            if is_trulens_enabled():
                try:
                    asyncio.create_task(
                        queue_rag_evaluation(
                            query=query_analysis.original_query,
                            response=english_response,
                            context_chunks=rag_result.reference_data.get("chunks", []) if rag_result.reference_data else [],
                            context_summaries=rag_result.reference_data.get("summaries", []) if rag_result.reference_data else [],
                            context_graph=rag_result.reference_data.get("graph_data", []) if rag_result.reference_data else [],
                            social_tipping_point=social_tipping_point,
                            session_id=session_id or "anonymous",
                            conversation_type=conversation_type,
                            metadata={
                                "difficulty_level": difficulty_level,
                                "has_relevant_data": has_relevant_data,
                                "sources_used": rag_result.sources_used if hasattr(rag_result, 'sources_used') else {}
                            }
                        )
                    )
                    logger.debug("TruLens evaluation queued for RAG response")
                except Exception as e:
                    logger.warning(f"Failed to queue TruLens evaluation: {e}")

            return result
        else:
            # Enhanced LLM fallback - get response first, then STP
            fallback_result = await self._generate_llm_fallback_response(
                query_analysis.original_query, difficulty_level, conversation_type
            )
            
            # Get STP based on fallback response content
            logger.info(f"🔍 Retrieving STP for fallback response (first 200 chars): {fallback_result['answer'][:200]}...")
            social_tipping_point = await self._get_stp_from_response(fallback_result["answer"])
            
            # Update fallback result with response-based STP
            fallback_result["social_tipping_point"] = social_tipping_point
            
            return fallback_result
    
    async def _get_stp_from_response(self, response_content: str) -> str:
        """
        Get STP based on LLM response content instead of user query.
        Uses the response to find relevant social tipping points.
        """
        try:
            self.performance_stats["stp_requests"] += 1
            self.performance_stats["stp_from_response"] += 1
            
            # Extract key concepts from response for STP search
            # Use first 500 characters or key sentences for STP retrieval
            stp_search_text = self._extract_key_content_for_stp(response_content)
            
            if is_langfuse_enabled():
                langfuse_client = get_langfuse_client()
                with langfuse_client.start_as_current_span(
                    name="stp_from_response",
                    input=stp_search_text[:200],
                    metadata={
                        "component": "stp_service",
                        "step": "response_based_stp",
                        "source": "llm_response",
                        "response_length": len(response_content)
                    }
                ) as span:
                    result = await self.stp_client.get_social_tipping_point(stp_search_text)
                    
                    span.update(
                        output=result[:200] if result else "No STP found",
                        metadata={
                            "stp_found": result != "No specific social tipping point available for this query.",
                            "stp_length": len(result) if result else 0,
                            "search_method": "response_based"
                        }
                    )
            else:
                result = await self.stp_client.get_social_tipping_point_silent(stp_search_text)
            
            # Update success stats
            if result != "No specific social tipping point available for this query.":
                self.performance_stats["stp_success_count"] += 1
                logger.info(f"✅ Found STP from response content")
            else:
                logger.info(f"ℹ️  No relevant STP found for response content")
            
            return result
            
        except Exception as e:
            logger.error(f"STP from response failed: {e}")
            return "No specific social tipping point available for this query."
    
    def _extract_key_content_for_stp(self, response_content: str) -> str:
        """
        Extract key content from LLM response for STP search.
        Focuses on the main topics and concepts rather than the entire response.
        """
        # Remove common conversational phrases
        content = response_content.lower()
        
        # Remove generic opening/closing phrases
        patterns_to_remove = [
            r"thank you for.*?\.",
            r"i (understand|hope|can|will).*?\.",
            r"feel free to.*?\.",
            r"if you (have|need|want).*?\.",
            r"let me know.*?\.",
        ]
        
        for pattern in patterns_to_remove:
            content = re.sub(pattern, "", content, flags=re.IGNORECASE)
        
        # Take the core content (middle section) which usually contains the main information
        sentences = [s.strip() for s in content.split('.') if len(s.strip()) > 20]
        
        # If we have multiple sentences, take the most substantive ones (skip first/last if generic)
        if len(sentences) > 3:
            # Take middle sentences which usually have core content
            key_sentences = sentences[1:-1][:3]  # Up to 3 middle sentences
        elif len(sentences) > 1:
            key_sentences = sentences[:2]
        else:
            key_sentences = sentences
        
        key_content = '. '.join(key_sentences)
        
        # Limit to reasonable length for STP search (500 chars)
        if len(key_content) > 500:
            key_content = key_content[:500]
        
        logger.debug(f"📝 Extracted key content for STP: {key_content[:150]}...")
        return key_content if key_content else response_content[:500]
    
    def _check_has_relevant_data(self, rag_result) -> bool:
        """Check if RAG result contains relevant data"""
        if not hasattr(rag_result, 'reference_data') or not rag_result.reference_data:
            return False
        
        reference_data = rag_result.reference_data
        chunks = reference_data.get("chunks", []) or []
        summaries = reference_data.get("summaries", []) or []
        graph_data = reference_data.get("graph_data", []) or []
        
        total_references = len(chunks) + len(summaries) + len(graph_data)
        if total_references == 0:
            return False
        
        # Check for meaningful similarity scores
        relevant_count = 0
        for item in chunks + summaries + graph_data:
            score = item.get("rerank_score", item.get("similarity_score", 0.0))
            if score >= 0.3:
                relevant_count += 1
        
        return relevant_count > 0
    
    async def _analyze_query(
        self, 
        question: str, 
        session_id: Optional[str], 
        language: str,
        conversation_type: str = "continue"
    ):
        """Analyze query with LLM preprocessor - conversation type aware"""
        from app.services.rag.llm_query_processor import get_llm_query_preprocessor
        
        preprocessor = await get_llm_query_preprocessor()
        
        # Only get context for CONTINUE conversations
        conversation_context = None
        if session_id and conversation_type == "continue":
            conversation_context = await self._get_conversation_context(session_id)
            logger.debug(f"📝 Loaded conversation context for continue conversation")
        elif conversation_type == "start":
            logger.debug(f"🆕 Start conversation - no context loaded")
        
        analysis = await preprocessor.analyze_query(question, conversation_context, language)
        return analysis
    
    async def _generate_sources(self, reference_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate sources with URL resolution"""
        if not reference_data:
            return {"sources": [], "total_references": 0}
        
        chunks = reference_data.get("chunks", []) or []
        summaries = reference_data.get("summaries", []) or []
        graph_data = reference_data.get("graph_data", []) or []
        
        try:
            result = await process_references_with_urls_and_count(chunks, summaries, graph_data)
            return result
            
        except Exception as e:
            logger.error(f"Error generating sources: {e}")
            return {"sources": [], "total_references": 0}
    
    async def _generate_llm_fallback_response(
        self, query: str, difficulty_level: str, conversation_type: str
    ) -> Dict[str, Any]:
        """ LLM fallback response with detailed logging."""
        
        try:
            fallback_start = time.perf_counter()
            self.performance_stats["fallback_responses"] += 1
            
            logger.info(f"🔄 Generating LLM fallback response for: '{query[:100]}...'")
            
            if is_langfuse_enabled():
                langfuse_client = get_langfuse_client()
                with langfuse_client.start_as_current_span(
                    name="llm_fallback",
                    input=query,
                    metadata={"component": "llm_fallback", "step": "fallback_generation", "language": "en"}
                ) as span:
                    
                    # Generate fallback response
                    fallback_response = await self._generate_fallback_response(
                        query, difficulty_level, conversation_type
                    )
                    
                    fallback_time = time.perf_counter() - fallback_start
                    
                    span.update(
                        output=fallback_response["content"][:300],
                        metadata={
                            "fallback_type": "enhanced",
                            "conversation_type": conversation_type,
                            "language": "en",
                            "generation_time": fallback_time,
                            "title": fallback_response["title"],
                            "content_length": len(fallback_response["content"])
                        }
                    )

                    return {
                        "answer": fallback_response["content"],
                        "title": fallback_response["title"],
                        "social_tipping_point": "No specific social tipping point available for this query.",
                        "sources": [],
                        "total_references": 0
                    }
            else:
                # No tracing version
                fallback_response = await self._generate_fallback_response(
                    query, difficulty_level, conversation_type
                )

                fallback_time = time.perf_counter() - fallback_start

                logger.info(f"✅ Fallback response generated in {fallback_time:.3f}s - Title: '{fallback_response['title']}'")

                return {
                    "answer": fallback_response["content"],
                    "title": fallback_response["title"],
                    "social_tipping_point": "No specific social tipping point available for this query.",
                    "sources": [],
                    "total_references": 0
                }
            
        except Exception as e:
            logger.error(f"Enhanced LLM fallback failed: {e}")
            return await self._generate_emergency_response(query)
    
    async def _generate_fallback_response(
        self, query: str, difficulty_level: str, conversation_type: str
    ) -> Dict[str, Any]:
        """Generate fallback response using LLM with PROPER response_generator parsing and title deduplication fix."""
        
        try:
            # Generate the prompt
            prompt = self.prompt_manager.render_llm_fallback_prompt(
                query=query,
                language="en",
                difficulty_level=difficulty_level,
                conversation_type=conversation_type
            )
            
            logger.debug(f"📝 Fallback prompt generated (length: {len(prompt)} chars)")
            
            raw_response = await self._call_llm(prompt)
            
            # ✅ LOGGING - Show what LLM actually returned
            logger.info(f"🔍 RAW LLM FALLBACK RESPONSE (first 500 chars):\n{raw_response[:500]}")
            logger.debug(f"📏 Full response length: {len(raw_response)} chars")
            
            # ✅ USE RESPONSE GENERATOR'S ROBUST PARSER
            # Import here to avoid circular dependency
            from app.services.rag.response_generator import get_response_generator_service
            response_gen = await get_response_generator_service()
            
            if conversation_type == "start":
                # Use start conversation parser
                title, content = response_gen._parse_start_response_robust(raw_response)
                
                # ✅ CRITICAL FIX: Remove title from content if LLM duplicated it
                # Check if content starts with the title (case-insensitive)
                if title and content.strip():
                    # Check for exact match at start
                    if content.startswith(title):
                        content = content[len(title):].strip()
                        logger.debug(f"🔧 Removed exact duplicate title from content")
                    # Check for title with newline
                    elif content.startswith(f"{title}\n"):
                        content = content[len(title)+1:].strip()
                        logger.debug(f"🔧 Removed title+newline from content")
                    # Check for title in first line (case-insensitive)
                    else:
                        first_line = content.split('\n')[0].strip()
                        if first_line.lower() == title.lower():
                            # Remove first line
                            content = '\n'.join(content.split('\n')[1:]).strip()
                            logger.debug(f"🔧 Removed title from first line of content")
            else:
                # Use continue conversation parser
                title = None  # No title for continue conversations
                content = response_gen._parse_continue_response_robust(raw_response)

            # ✅ ENHANCED LOGGING - Show parsing results
            logger.info(f"✅ PARSED RESULT - Title: '{title}' | Content length: {len(content)} chars")
            logger.debug(f"📝 Content preview: {content[:200]}...")
            
            # Check if we got default values (parsing failure indicator)
            if title == "Climate Information" and content == "I can provide climate information based on my training.":
                logger.warning(f"⚠️ Parser returned DEFAULT values - parsing likely failed!")
                logger.warning(f"🔍 Raw response structure check:")
                logger.warning(f"   - Contains '===TITLE_START===': {'===TITLE_START===' in raw_response}")
                logger.warning(f"   - Contains '<TITLE>': {'<TITLE>' in raw_response}")
                logger.warning(f"   - First 100 chars: {raw_response[:100]}")
                self.performance_stats["parsing_failures"] += 1
            
            # Add disclaimer
            disclaimer = self._get_disclaimer()
            enhanced_content = f"{disclaimer}\n\n{content}"
            # enhanced_content = f"{content}"
            
            return {
                "title": title,
                "content": enhanced_content
            }
            
        except Exception as e:
            logger.error(f"Fallback generation failed: {e}", exc_info=True)
            return {
                "title": "Climate Assistant",
                "content": f"I don't have specific information about '{query}' in my knowledge base. Please feel free to rephrase your question or ask about other climate topics."
            }
    
    def _get_default_greeting(self) -> str:
        """Get default greeting"""
        return "Hello! I'm NeuroClima Bot, your AI assistant for climate policy and environmental topics. How can I help you today?"
    
    # Additional helper methods
    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt"""
        from app.services.llm.factory import get_llm
        
        llm = await get_llm()
        if hasattr(llm, '_acall'):
            return await llm._acall(prompt)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, llm, prompt)
    
    async def _get_conversation_context(self, session_id: str) -> Optional[str]:
        """Get conversation context with more detailed history"""
        try:
            from uuid import UUID
            session_uuid = UUID(session_id)
            conv_memory = await get_conversation_memory(session_uuid)
            memory_vars = conv_memory.get_memory_variables()
            
            chat_history = memory_vars.get("chat_history", [])
            if chat_history:
                # Get more context for better enhancement (last 6 messages instead of 4)
                context = self._format_chat_history_detailed(chat_history[-6:])
                logger.debug(f"📝 Retrieved conversation context: {len(context)} chars")
                return context
            
        except Exception as e:
            logger.warning(f"Could not get conversation context: {e}")
        return None
    
    def _format_chat_history_detailed(self, chat_history: List) -> str:
        """Format chat history with more detail for context"""
        context_parts = []
        for i, message in enumerate(chat_history):
            if hasattr(message, 'content'):
                role = "User" if i % 2 == 0 else "Assistant"
                # Keep more content for better context understanding
                content = message.content[:300] + "..." if len(message.content) > 300 else message.content
                context_parts.append(f"{role}: {content}")
        
        formatted_context = "\n".join(context_parts)
        logger.debug(f"📝 Formatted context: {formatted_context[:200]}...")
        return formatted_context
    
    async def _get_conversation_memory(self, session_id: str) -> str:
        """Get formatted conversation memory"""
        context = await self._get_conversation_context(session_id)
        return context or ""
    
    def _get_disclaimer(self) -> str:
        """Get knowledge gap disclaimer"""
        return "I didn't find specific documents in my knowledge base for this query, so I'm providing information based on my general training about climate and environmental topics."

    async def _generate_error_response(self, query: str, error: str) -> Dict[str, Any]:
        """Generate error response"""
        return {
            "answer": f"I encountered a technical issue while processing your question about '{query}'. Please try again or rephrase your question.",
            "title": "Technical Issue",
            "social_tipping_point": "No specific social tipping point available for this query.",
            "sources": [],
            "total_references": 0
        }
    
    async def _generate_emergency_response(self, query: str) -> Dict[str, Any]:
        """Generate emergency response"""
        try:
            response_content = self.prompt_manager.render_emergency_response_prompt(
                query=query, language="en"
            )
            
            return {
                'answer': response_content,
                'title': 'Climate Assistant',
                'social_tipping_point': 'No specific social tipping point available for this query.',
                'sources': [],
                'total_references': 0
            }
            
        except Exception as e:
            logger.error(f"Emergency response failed: {e}")
            return self._get_hardcoded_emergency_response(query)
    
    def _get_hardcoded_emergency_response(self, query: str) -> Dict[str, Any]:
        """Final hardcoded emergency response"""
        return {
            'answer': f"I apologize, but I'm experiencing technical difficulties processing your question about '{query}'. Please try rephrasing your question or ask about a specific climate topic.",
            'title': 'Technical Difficulty',
            'social_tipping_point': 'No specific social tipping point available for this query.',
            'sources': [],
            'total_references': 0
        }
    
    def _update_performance_stats(self, total_time: float, retrieval_time: float, llm_time: float):
        """Update internal performance statistics"""
        try:
            total_queries = self.performance_stats["total_queries"]
            
            # Update running averages
            current_avg_response = self.performance_stats["avg_response_time"]
            self.performance_stats["avg_response_time"] = (
                (current_avg_response * (total_queries - 1) + total_time) / total_queries
            )
            
            if retrieval_time > 0:
                current_avg_retrieval = self.performance_stats["avg_retrieval_time"]
                retrieval_queries = self.performance_stats["substantive_queries"]
                if retrieval_queries > 0:
                    self.performance_stats["avg_retrieval_time"] = (
                        (current_avg_retrieval * (retrieval_queries - 1) + retrieval_time) / retrieval_queries
                    )
            
            if llm_time > 0:
                current_avg_llm = self.performance_stats["avg_llm_time"]
                self.performance_stats["avg_llm_time"] = (
                    (current_avg_llm * (total_queries - 1) + llm_time) / total_queries
                )
                
        except Exception as e:
            logger.error(f"Error updating performance stats: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive RAG service statistics with response-based STP integration"""
        try:
            if not self.is_initialized:
                return {"initialized": False}
            
            # Get orchestrator stats
            orchestrator_stats = await self.orchestrator.health_check()
            prompt_manager_ok = await self.prompt_manager.health_check()
            stp_health = await self.stp_client.health_check() if self.stp_client else False
            
            # Calculate source breakdown metrics
            total_queries = self.performance_stats["total_queries"]
            rag_response_rate = (
                self.performance_stats["rag_responses"] / total_queries 
                if total_queries > 0 else 0.0
            )
            bot_identity_rate = (
                self.performance_stats["bot_identity_queries"] / total_queries 
                if total_queries > 0 else 0.0
            )
            
            # Calculate processing breakdown
            start_processing_rate = (
                self.performance_stats["start_basic_fixes"] / total_queries 
                if total_queries > 0 else 0.0
            )
            continue_processing_rate = (
                self.performance_stats["continue_full_processing"] / total_queries 
                if total_queries > 0 else 0.0
            )
            
            # Calculate STP statistics
            stp_success_rate = (
                self.performance_stats["stp_success_count"] / self.performance_stats["stp_requests"]
                if self.performance_stats["stp_requests"] > 0 else 0.0
            )
            stp_from_response_rate = (
                self.performance_stats["stp_from_response"] / total_queries 
                if total_queries > 0 else 0.0
            )
            
            # Calculate fallback and parsing stats
            fallback_rate = (
                self.performance_stats["fallback_responses"] / total_queries
                if total_queries > 0 else 0.0
            )
            parsing_failure_rate = (
                self.performance_stats["parsing_failures"] / self.performance_stats["fallback_responses"]
                if self.performance_stats["fallback_responses"] > 0 else 0.0
            )
            
            # Combine all stats
            return {
                "initialized": True,
                "performance_stats": {
                    **self.performance_stats,
                    "rag_response_rate": rag_response_rate,
                    "bot_identity_rate": bot_identity_rate,
                    "start_processing_rate": start_processing_rate,
                    "continue_processing_rate": continue_processing_rate,
                    "stp_success_rate": stp_success_rate,
                    "stp_from_response_rate": stp_from_response_rate,
                    "fallback_rate": fallback_rate,
                    "parsing_failure_rate": parsing_failure_rate
                },
                "orchestrator": orchestrator_stats,
                "prompt_manager": prompt_manager_ok,
                "stp_service": stp_health,
                "overall_health": orchestrator_stats.get("overall", False) and prompt_manager_ok,
                # Processing tracking
                "processing_tracking": {
                    "pure_english_processing": True,
                    "start_basic_fixes": self.performance_stats["start_basic_fixes"],
                    "continue_full_processing": self.performance_stats["continue_full_processing"],
                    "translation_at_boundaries_only": True,
                    "stp_integration_enabled": True,
                    "stp_method": "response_based",
                    "stp_from_llm_response": True,
                    "conversation_type_aware": True,
                    "fallback_responses": self.performance_stats["fallback_responses"],
                    "parsing_failures": self.performance_stats["parsing_failures"],
                    "title_deduplication_fix": True
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting RAG stats: {e}")
            return {
                "initialized": self.is_initialized,
                "error": str(e),
                "performance_stats": self.performance_stats.copy()
            }
    
    async def health_check(self) -> bool:
        """Health check with STP integration"""
        try:
            if not self.is_initialized:
                return False
            
            orchestrator_ok = await self.orchestrator.health_check()
            prompt_manager_ok = await self.prompt_manager.health_check()
            
            # STP health is optional - system can work without it
            stp_ok = True
            try:
                stp_ok = await self.stp_client.health_check() if self.stp_client else False
                if not stp_ok:
                    logger.warning("STP service is unhealthy, but system continues with fallback")
            except Exception as e:
                logger.warning(f"STP health check failed: {e}, but system continues")
                stp_ok = False
            
            core_health = orchestrator_ok.get("overall", False) and prompt_manager_ok
            return core_health
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# Global service instance
clean_rag_service = CleanRAGService()


async def get_rag_service() -> CleanRAGService:
    """Get the clean RAG service instance"""
    if not clean_rag_service.is_initialized:
        await clean_rag_service.initialize()
    return clean_rag_service