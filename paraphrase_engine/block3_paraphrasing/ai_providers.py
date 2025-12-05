"""
AI Provider implementations for different services
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import httpx

# AI SDK imports
try:
    import openai
except ImportError:
    openai = None

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from ..config import settings

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    def __init__(self, api_key: str, model: str, name: str):
        self.api_key = api_key
        self.model = model
        self.name = name
        self.client = None
        self._initialize_client()
    
    @abstractmethod
    def _initialize_client(self):
        """Initialize the API client"""
        pass
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Generate text based on prompt"""
        pass


class OpenAIProvider(AIProvider):
    """OpenAI GPT provider"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        super().__init__(api_key, model, "OpenAI")
    
    def _initialize_client(self):
        """Initialize OpenAI client"""
        if not openai:
            raise ImportError("OpenAI package not installed")
        
        self.client = openai.AsyncOpenAI(api_key=self.api_key)
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Generate text using OpenAI"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional text paraphrasing assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=settings.ai_timeout_seconds
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            raise


class AnthropicProvider(AIProvider):
    """Anthropic Claude provider"""
    
    def __init__(self, api_key: str, model: str = None):
        # Use Claude Sonnet 4.5 as default (cost-effective)
        # Correct model ID as of November 2025: claude-sonnet-4-5-20250929
        if model is None:
            model = "claude-sonnet-4-5-20250929"
        super().__init__(api_key, model, "Anthropic")
        # List of fallback models to try if primary fails
        self.fallback_models = [
            "claude-sonnet-4-5-20250929",  # Claude Sonnet 4.5 (primary, correct ID)
            "claude-3-5-sonnet-20240620",   # Claude 3.5 Sonnet (stable)
            "claude-3-sonnet-20240229",     # Claude 3 Sonnet (reliable)
            "claude-3-haiku-20240307",      # Claude 3 Haiku (fastest and cheapest)
            "claude-opus-4-5-20251101",      # Claude Opus 4.5 (expensive, last resort)
            "claude-3-opus-20240229"        # Claude 3 Opus (expensive, last resort)
        ]
    
    def _initialize_client(self):
        """Initialize Anthropic client"""
        if not anthropic:
            raise ImportError("Anthropic package not installed")
        
        try:
            self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
            # Test that the client has the messages attribute
            if not hasattr(self.client, 'messages'):
                raise AttributeError(
                    "Anthropic client does not have 'messages' attribute. "
                    "Please upgrade anthropic package: pip install --upgrade anthropic"
                )
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
            raise
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Generate text using Anthropic Claude with fallback models"""
        # Check if client is properly initialized
        if not hasattr(self.client, 'messages'):
            raise AttributeError(
                "Anthropic client does not have 'messages' attribute. "
                "Please upgrade anthropic package: pip install --upgrade anthropic"
            )
        
        # Try primary model first, then fallbacks
        models_to_try = [self.model] + [m for m in self.fallback_models if m != self.model]
        last_error = None
        
        for model_name in models_to_try:
            try:
                response = await self.client.messages.create(
                    model=model_name,
                    messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=settings.ai_timeout_seconds
                )
                
                # Extract text from response
                if response.content and len(response.content) > 0:
                    content_item = response.content[0]
                    if hasattr(content_item, 'text'):
                        result = content_item.text.strip()
                        if model_name != self.model:
                            logger.info(f"Successfully used fallback model: {model_name}")
                        return result
                    elif isinstance(content_item, str):
                        result = content_item.strip()
                        if model_name != self.model:
                            logger.info(f"Successfully used fallback model: {model_name}")
                        return result
                
                raise ValueError(f"Empty response from model {model_name}")
            
            except Exception as e:
                last_error = e
                error_str = str(e)
                if "404" in error_str or "not_found" in error_str.lower():
                    logger.warning(f"Model {model_name} not found (404), trying fallback models...")
                    continue
                logger.debug(f"Error with model {model_name}: {e}")
                continue
        
        # If all models failed, raise the last error
        if last_error:
            logger.error(f"All Anthropic models failed. Last error: {last_error}")
            raise last_error
        else:
            raise ValueError("Failed to generate response from any Anthropic model")


class GoogleGeminiProvider(AIProvider):
    """Google Gemini provider"""
    
    def __init__(self, api_key: str, model: str = None):
        # Default to Gemini 2.5 Pro
        if model is None:
            model = "gemini-2.5-pro"
        super().__init__(api_key, model, "Google Gemini")
    
    def _initialize_client(self):
        """Initialize Gemini client with automatic model selection"""
        if not genai:
            raise ImportError("Google GenerativeAI package not installed")
        
        genai.configure(api_key=self.api_key)
        
        # List of models to try in order of preference
        models_to_try = [
            self.model,  # Try the specified model first
            "gemini-2.5-pro",
            "gemini-2.5-pro-latest",
            "models/gemini-2.5-pro",
            "models/gemini-2.5-pro-latest",
            "gemini-1.5-pro-latest",
            "gemini-1.5-pro",
            "models/gemini-1.5-pro-latest",
            "models/gemini-1.5-pro",
        ]
        
        last_error = None
        for model_name in models_to_try:
            try:
                self.client = genai.GenerativeModel(model_name)
                self.model = model_name
                logger.info(f"Successfully initialized Gemini with model: {model_name}")
                return
            except Exception as e:
                last_error = e
                logger.debug(f"Failed to initialize with model '{model_name}': {e}")
                continue
        
        # If all models failed, raise error
        raise ImportError(
            f"Failed to initialize any Gemini model. Last error: {last_error}. "
            f"Please check your API key and ensure it has access to Gemini models."
        )
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Generate text using Google Gemini"""
        # Increase max_tokens for Gemini - it can handle up to 8192 output tokens
        # For long input texts, we need more output tokens
        # Calculate based on input length: roughly 2x input length + base
        input_length = len(prompt)
        calculated_max = max(input_length * 2, 8000)  # At least 8000 tokens for long texts
        effective_max_tokens = max(max_tokens, calculated_max, 8000)
        
        try:
            # Gemini uses a different parameter structure
            generation_config = genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=effective_max_tokens,
            )
            
            # Run in executor since Gemini SDK might not be async
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.generate_content(
                    prompt,
                    generation_config=generation_config
                )
            )
            
            # Check if response has candidates
            if not response.candidates:
                logger.warning("Gemini response has no candidates")
                raise ValueError("Gemini API returned no candidates")
            
            # Get the first candidate
            candidate = response.candidates[0]
            
            # Check finish_reason
            finish_reason = candidate.finish_reason if hasattr(candidate, 'finish_reason') else None
            
            # Handle different finish reasons
            if finish_reason == 2:  # MAX_TOKENS - response was truncated
                logger.warning(
                    f"Gemini response was truncated (MAX_TOKENS reached). "
                    f"Consider increasing max_tokens. Current: {effective_max_tokens}"
                )
                # Try to get partial text if available
                if candidate.content and candidate.content.parts:
                    text_parts = []
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)
                    if text_parts:
                        return " ".join(text_parts).strip()
                    else:
                        raise ValueError(
                            "Gemini response was truncated and no text parts available. "
                            "Try increasing max_tokens or shortening the input."
                        )
                else:
                    raise ValueError(
                        "Gemini response was truncated (MAX_TOKENS) and no content available. "
                        "Try increasing max_tokens or shortening the input."
                    )
            elif finish_reason == 3:  # SAFETY - content was blocked
                logger.warning("Gemini response was blocked due to safety filters")
                raise ValueError("Gemini API blocked the response due to safety filters")
            elif finish_reason == 4:  # RECITATION - potential copyright issue
                logger.warning("Gemini response was blocked due to recitation concerns")
                raise ValueError("Gemini API blocked the response due to recitation concerns")
            
            # Normal case - try to get text
            try:
                if hasattr(response, 'text') and response.text:
                    return response.text.strip()
            except Exception as text_error:
                logger.debug(f"Could not access response.text: {text_error}")
            
            # Fallback: try to extract from candidate content
            if candidate.content and candidate.content.parts:
                text_parts = []
                for part in candidate.content.parts:
                    if hasattr(part, 'text') and part.text:
                        text_parts.append(part.text)
                if text_parts:
                    return " ".join(text_parts).strip()
            
            # If we get here, we couldn't extract any text
            raise ValueError(
                f"Could not extract text from Gemini response. "
                f"Finish reason: {finish_reason}, "
                f"Candidates: {len(response.candidates) if response.candidates else 0}"
            )
            
        except ValueError:
            # Re-raise ValueError as-is (these are our custom errors)
            raise
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            raise


class FallbackProvider(AIProvider):
    """Fallback provider using HTTP API calls"""
    
    def __init__(self, api_key: str, endpoint: str, model: str = "default"):
        self.endpoint = endpoint
        super().__init__(api_key, model, "Fallback")
    
    def _initialize_client(self):
        """Initialize HTTP client"""
        self.client = httpx.AsyncClient(
            timeout=settings.ai_timeout_seconds,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Generate text using HTTP API"""
        try:
            response = await self.client.post(
                self.endpoint,
                json={
                    "prompt": prompt,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "model": self.model
                }
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("text", "").strip()
            
        except Exception as e:
            logger.error(f"Fallback provider error: {e}")
            raise
