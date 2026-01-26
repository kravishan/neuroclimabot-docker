"""AWS Bedrock LLM implementation with async semaphore control."""

import asyncio
import json
from typing import Any, Dict, List, Optional

from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.llms.base import LLM
from pydantic import Field

from app.core.exceptions import LLMError
from app.core.dependencies import get_semaphore_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BedrockLLM(LLM):
    """AWS Bedrock LLM implementation using boto3."""

    region: str = Field(default="us-east-1")
    model_id: str = Field(default="anthropic.claude-3-sonnet-20240229-v1:0")
    access_key_id: Optional[str] = Field(default=None)
    secret_access_key: Optional[str] = Field(default=None)
    endpoint_url: Optional[str] = Field(default=None)
    temperature: float = Field(default=0.2)
    max_tokens: int = Field(default=1500)
    timeout: int = Field(default=60)

    _client: Any = None

    @property
    def _llm_type(self) -> str:
        return "bedrock"

    def _get_client(self):
        """Get or create the Bedrock runtime client."""
        if self._client is None:
            try:
                import boto3
                from botocore.config import Config

                boto_config = Config(
                    read_timeout=self.timeout,
                    connect_timeout=10,
                    retries={'max_attempts': 3}
                )

                client_kwargs = {
                    "service_name": "bedrock-runtime",
                    "region_name": self.region,
                    "config": boto_config
                }

                # Use explicit credentials if provided
                if self.access_key_id and self.secret_access_key:
                    client_kwargs["aws_access_key_id"] = self.access_key_id
                    client_kwargs["aws_secret_access_key"] = self.secret_access_key

                # Use custom endpoint if provided
                if self.endpoint_url:
                    client_kwargs["endpoint_url"] = self.endpoint_url

                self._client = boto3.client(**client_kwargs)

            except ImportError:
                raise LLMError("boto3 is required for AWS Bedrock. Install it with: pip install boto3")
            except Exception as e:
                raise LLMError(f"Failed to create Bedrock client: {str(e)}")

        return self._client

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call the Bedrock model synchronously."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self._acall(prompt, stop, run_manager, **kwargs)
        )

    async def _acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """
        Call the Bedrock model asynchronously with semaphore control.

        Limits concurrent Bedrock API calls to prevent overload and
        manage resource usage across the application.
        """
        semaphore_manager = get_semaphore_manager()

        logger.debug("Waiting for LLM semaphore (Bedrock)...")
        async with semaphore_manager.llm_semaphore:
            logger.debug("LLM semaphore acquired (Bedrock)")

            try:
                client = self._get_client()

                # Build the request body based on the model type
                body = self._build_request_body(prompt, stop)

                # Run the synchronous boto3 call in a thread pool
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: client.invoke_model(
                        modelId=self.model_id,
                        body=json.dumps(body),
                        contentType="application/json",
                        accept="application/json"
                    )
                )

                # Parse the response
                response_body = json.loads(response["body"].read())
                result = self._parse_response(response_body)

                logger.debug("LLM semaphore released (Bedrock)")
                return result

            except Exception as e:
                error_msg = str(e)
                if "ExpiredTokenException" in error_msg:
                    raise LLMError("AWS credentials have expired. Please refresh your credentials.")
                elif "AccessDeniedException" in error_msg:
                    raise LLMError("Access denied to Bedrock. Check your IAM permissions.")
                elif "ValidationException" in error_msg:
                    raise LLMError(f"Invalid request to Bedrock: {error_msg}")
                elif "ThrottlingException" in error_msg:
                    raise LLMError("Bedrock API rate limit exceeded. Please try again later.")
                else:
                    raise LLMError(f"Bedrock error: {error_msg}")

    def _build_request_body(self, prompt: str, stop: Optional[List[str]] = None) -> Dict[str, Any]:
        """Build the request body based on the model type."""

        # Anthropic Claude models
        if "anthropic" in self.model_id.lower() or "claude" in self.model_id.lower():
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            if stop:
                body["stop_sequences"] = stop
            return body

        # Amazon Titan models
        elif "titan" in self.model_id.lower():
            body = {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": self.max_tokens,
                    "temperature": self.temperature,
                    "topP": 0.9
                }
            }
            if stop:
                body["textGenerationConfig"]["stopSequences"] = stop
            return body

        # Meta Llama models
        elif "llama" in self.model_id.lower() or "meta" in self.model_id.lower():
            body = {
                "prompt": prompt,
                "max_gen_len": self.max_tokens,
                "temperature": self.temperature,
                "top_p": 0.9
            }
            return body

        # Mistral models on Bedrock
        elif "mistral" in self.model_id.lower():
            body = {
                "prompt": f"<s>[INST] {prompt} [/INST]",
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": 0.9
            }
            if stop:
                body["stop"] = stop
            return body

        # Cohere models
        elif "cohere" in self.model_id.lower():
            body = {
                "prompt": prompt,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
            }
            if stop:
                body["stop_sequences"] = stop
            return body

        # AI21 Jurassic models
        elif "ai21" in self.model_id.lower() or "jurassic" in self.model_id.lower():
            body = {
                "prompt": prompt,
                "maxTokens": self.max_tokens,
                "temperature": self.temperature,
            }
            if stop:
                body["stopSequences"] = stop
            return body

        # Default: Use Anthropic Claude format
        else:
            logger.warning(f"Unknown model type: {self.model_id}, using Claude format")
            return {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }

    def _parse_response(self, response_body: Dict[str, Any]) -> str:
        """Parse the response based on the model type."""

        # Anthropic Claude models
        if "content" in response_body and isinstance(response_body.get("content"), list):
            return response_body["content"][0].get("text", "").strip()

        # Amazon Titan models
        elif "results" in response_body:
            results = response_body["results"]
            if results and len(results) > 0:
                return results[0].get("outputText", "").strip()

        # Meta Llama models
        elif "generation" in response_body:
            return response_body["generation"].strip()

        # Mistral models
        elif "outputs" in response_body:
            outputs = response_body["outputs"]
            if outputs and len(outputs) > 0:
                return outputs[0].get("text", "").strip()

        # Cohere models
        elif "generations" in response_body:
            generations = response_body["generations"]
            if generations and len(generations) > 0:
                return generations[0].get("text", "").strip()

        # AI21 models
        elif "completions" in response_body:
            completions = response_body["completions"]
            if completions and len(completions) > 0:
                return completions[0].get("data", {}).get("text", "").strip()

        # Fallback: try common fields
        for field in ["text", "output", "response", "generated_text"]:
            if field in response_body:
                return str(response_body[field]).strip()

        logger.warning(f"Could not parse Bedrock response: {response_body}")
        return str(response_body)

    async def test_connection(self) -> bool:
        """Test connection to AWS Bedrock."""
        try:
            client = self._get_client()

            # Build a minimal test request
            test_body = self._build_request_body("Hello", None)

            # Override max_tokens for quick test
            if "max_tokens" in test_body:
                test_body["max_tokens"] = 10
            elif "maxTokens" in test_body:
                test_body["maxTokens"] = 10
            elif "max_gen_len" in test_body:
                test_body["max_gen_len"] = 10
            elif "textGenerationConfig" in test_body:
                test_body["textGenerationConfig"]["maxTokenCount"] = 10

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(test_body),
                    contentType="application/json",
                    accept="application/json"
                )
            )

            response_body = json.loads(response["body"].read())
            result = self._parse_response(response_body)
            return bool(result)

        except Exception as e:
            logger.error(f"Failed to connect to AWS Bedrock: {e}")
            return False

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """Return identifying parameters."""
        return {
            "model_id": self.model_id,
            "region": self.region,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
