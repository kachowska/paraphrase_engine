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
    
    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229"):
        super().__init__(api_key, model, "Anthropic")
    
    def _initialize_client(self):
        """Initialize Anthropic client"""
        if not anthropic:
            raise ImportError("Anthropic package not installed")
        
        self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Generate text using Anthropic Claude"""
        try:
            response = await self.client.messages.create(
                model=self.model,
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
                return response.content[0].text.strip()
            
            return ""
            
        except Exception as e:
            logger.error(f"Anthropic generation error: {e}")
            raise


class GoogleGeminiProvider(AIProvider):
    """Google Gemini provider"""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        super().__init__(api_key, model, "Google Gemini")
    
    def _initialize_client(self):
        """Initialize Gemini client"""
        if not genai:
            raise ImportError("Google GenerativeAI package not installed")
        
        genai.configure(api_key=self.api_key)
        self.client = genai.GenerativeModel(self.model)
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Generate text using Google Gemini"""
        try:
            # Gemini uses a different parameter structure
            generation_config = genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
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
            
            return response.text.strip()
            
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
