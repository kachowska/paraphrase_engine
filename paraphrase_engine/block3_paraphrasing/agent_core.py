"""
Block 3: Paraphrasing Agent Core
The "secret sauce" - generates the best paraphrased text using multiple AI models
"""

import asyncio
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from tenacity import retry, stop_after_attempt, wait_exponential
import json

from ..config import settings
from .ai_providers import (
    OpenAIProvider,
    AnthropicProvider,
    GoogleGeminiProvider,
    AIProvider
)
from ..block5_logging.logger import SystemLogger

logger = logging.getLogger(__name__)


@dataclass
class ParaphraseCandidate:
    """Represents a paraphrase candidate from an AI model"""
    provider: str
    original_text: str
    paraphrased_text: str
    score: float = 0.0
    metadata: Dict[str, Any] = None


class ParaphrasingAgent:
    """
    Multi-agent paraphrasing system that:
    1. Generates multiple versions using different AI models
    2. Evaluates and selects the best version
    3. Applies final humanization
    """
    
    def __init__(self):
        self.system_logger = SystemLogger()
        self.providers: List[AIProvider] = []
        self._initialize_providers()
        
        # Prompts for different stages
        self.generation_prompt_template = """
You are an expert in academic and scientific writing. Your task is to paraphrase the following text while:
1. Preserving the exact meaning and all key information
2. Maintaining the academic/scientific style and terminology
3. Ensuring the new version is significantly different from the original
4. Keeping the same level of formality and technical precision

Original text:
{text}

Provide ONLY the paraphrased version, without any explanations or metadata.
"""
        
        self.evaluation_prompt_template = """
You are an expert evaluator of paraphrased text. Compare these paraphrased versions and select the BEST one based on:

1. Preservation of original meaning (40% weight)
2. Maintenance of academic/scientific style (30% weight)
3. Dissimilarity from the original (30% weight)

Original text:
{original}

Candidates:
{candidates}

Respond with a JSON object containing:
{{
    "best_index": <index of the best candidate, starting from 0>,
    "scores": [<score for candidate 0>, <score for candidate 1>, ...],
    "reasoning": "brief explanation"
}}
"""
        
        self.humanization_prompt_template = """
You are a final editor. Take this paraphrased text and make subtle adjustments to ensure it reads naturally and avoids AI detection patterns, while maintaining accuracy and academic style.

Make minimal changes - only what's necessary to improve natural flow.

Text to refine:
{text}

Provide ONLY the refined version, without any explanations.
"""
    
    def _initialize_providers(self):
        """Initialize available AI providers based on configuration - using only Gemini"""
        
        # Используем только Google Gemini
        if settings.google_api_key:
            try:
                provider = GoogleGeminiProvider(api_key=settings.google_api_key)
                self.providers.append(provider)
                logger.info("Initialized Google Gemini provider")
            except Exception as e:
                logger.warning(f"Failed to initialize Google Gemini provider: {e}")
        else:
            raise ValueError("Google API key is required. Please configure GOOGLE_API_KEY in .env file.")
        
        # OpenAI отключен из-за проблем с кодировкой Unicode
        # if settings.openai_api_key:
        #     try:
        #         provider = OpenAIProvider(api_key=settings.openai_api_key)
        #         self.providers.append(provider)
        #         logger.info("Initialized OpenAI provider")
        #     except Exception as e:
        #         logger.warning(f"Failed to initialize OpenAI provider: {e}")
        
        # Anthropic отключен - используем только Gemini
        # if settings.anthropic_api_key:
        #     try:
        #         provider = AnthropicProvider(api_key=settings.anthropic_api_key)
        #         self.providers.append(provider)
        #         logger.info("Initialized Anthropic provider")
        #     except Exception as e:
        #         logger.warning(f"Failed to initialize Anthropic provider: {e}")
        
        if not self.providers:
            raise ValueError("No AI providers available. Please configure GOOGLE_API_KEY in .env file.")
        
        logger.info(f"Initialized {len(self.providers)} AI provider(s) - using only Google Gemini")
    
    async def paraphrase(
        self,
        text: str,
        style: str = "scientific-legal",
        task_id: Optional[str] = None,
        fragment_index: Optional[int] = None
    ) -> str:
        """
        Main paraphrasing method - orchestrates the multi-stage process
        """
        try:
            # Log start
            await self.system_logger.log_paraphrase_start(
                task_id=task_id,
                fragment_index=fragment_index,
                text_length=len(text)
            )
            
            # Stage 1: Generate multiple candidates
            candidates = await self._generate_candidates(text, style)
            
            if not candidates:
                logger.error("No candidates generated")
                raise Exception("Failed to generate paraphrase candidates")
            
            # If only one candidate, skip evaluation
            if len(candidates) == 1:
                best_candidate = candidates[0]
            else:
                # Stage 2: Evaluate and select best candidate
                best_candidate = await self._evaluate_candidates(text, candidates)
            
            # Stage 3: Apply final humanization
            final_text = await self._humanize_text(best_candidate.paraphrased_text)
            
            # Log completion
            await self.system_logger.log_paraphrase_complete(
                task_id=task_id,
                fragment_index=fragment_index,
                provider_used=best_candidate.provider,
                original_text=text,
                paraphrased_text=final_text
            )
            
            return final_text
            
        except Exception as e:
            logger.error(f"Error in paraphrase process: {e}")
            
            # Log error
            await self.system_logger.log_error(
                chat_id=0,  # Will be updated by caller
                operation=f"paraphrase_fragment_{fragment_index}",
                error_message=str(e)
            )
            
            # Return original text as fallback
            return text
    
    async def _generate_candidates(self, text: str, style: str) -> List[ParaphraseCandidate]:
        """Generate paraphrase candidates from multiple AI providers"""
        candidates = []
        
        # Prepare prompt
        prompt = self.generation_prompt_template.format(text=text)
        
        # Create tasks for parallel execution
        tasks = []
        for provider in self.providers:
            task = self._generate_with_provider(provider, prompt, text)
            tasks.append(task)
        
        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Provider {self.providers[i].name} failed: {result}")
                continue
            
            if result:
                candidates.append(result)
                logger.info(f"Generated candidate from {result.provider}")
        
        return candidates
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _generate_with_provider(
        self,
        provider: AIProvider,
        prompt: str,
        original_text: str
    ) -> Optional[ParaphraseCandidate]:
        """Generate a single candidate with retry logic"""
        try:
            paraphrased = await provider.generate(
                prompt=prompt,
                temperature=settings.ai_temperature,
                max_tokens=settings.ai_max_tokens
            )
            
            if paraphrased and paraphrased.strip():
                return ParaphraseCandidate(
                    provider=provider.name,
                    original_text=original_text,
                    paraphrased_text=paraphrased.strip(),
                    metadata={"model": provider.model}
                )
            
        except Exception as e:
            logger.error(f"Error with provider {provider.name}: {e}")
            raise
        
        return None
    
    async def _evaluate_candidates(
        self,
        original_text: str,
        candidates: List[ParaphraseCandidate]
    ) -> ParaphraseCandidate:
        """Evaluate candidates and select the best one"""
        
        if len(candidates) == 1:
            return candidates[0]
        
        # Prepare candidates for evaluation
        candidates_text = "\n".join([
            f"Candidate {i}: {c.paraphrased_text}"
            for i, c in enumerate(candidates)
        ])
        
        # Prepare evaluation prompt
        prompt = self.evaluation_prompt_template.format(
            original=original_text,
            candidates=candidates_text
        )
        
        # Use the first available provider for evaluation
        evaluator_provider = self.providers[0]
        
        try:
            evaluation_response = await evaluator_provider.generate(
                prompt=prompt,
                temperature=0.3,  # Lower temperature for more consistent evaluation
                max_tokens=500
            )
            
            # Parse evaluation response
            try:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', evaluation_response, re.DOTALL)
                if json_match:
                    evaluation_data = json.loads(json_match.group())
                    best_index = evaluation_data.get("best_index", 0)
                    scores = evaluation_data.get("scores", [])
                    
                    # Validate index
                    if 0 <= best_index < len(candidates):
                        best_candidate = candidates[best_index]
                        if scores and best_index < len(scores):
                            best_candidate.score = scores[best_index]
                        
                        logger.info(f"Selected candidate {best_index} from {best_candidate.provider}")
                        return best_candidate
            except json.JSONDecodeError:
                logger.warning("Failed to parse evaluation response as JSON")
            
            # Fallback: return first candidate
            logger.warning("Evaluation failed, using first candidate")
            return candidates[0]
            
        except Exception as e:
            logger.error(f"Error in evaluation: {e}")
            # Return first candidate as fallback
            return candidates[0]
    
    async def _humanize_text(self, text: str) -> str:
        """Apply final humanization to the text"""
        
        # If no providers available, return original
        if not self.providers:
            return text
        
        # Use a different provider for humanization if available
        provider = self.providers[-1] if len(self.providers) > 1 else self.providers[0]
        
        prompt = self.humanization_prompt_template.format(text=text)
        
        try:
            humanized = await provider.generate(
                prompt=prompt,
                temperature=0.5,
                max_tokens=settings.ai_max_tokens
            )
            
            if humanized and humanized.strip():
                logger.info("Applied humanization successfully")
                return humanized.strip()
            
        except Exception as e:
            logger.warning(f"Humanization failed: {e}")
        
        # Return original if humanization fails
        return text
    
    async def test_providers(self) -> Dict[str, bool]:
        """Test all configured providers"""
        results = {}
        test_text = "This is a test sentence for provider validation."
        
        for provider in self.providers:
            try:
                response = await provider.generate(
                    prompt=f"Echo this exactly: {test_text}",
                    temperature=0.1,
                    max_tokens=50
                )
                results[provider.name] = bool(response)
            except Exception as e:
                logger.error(f"Provider {provider.name} test failed: {e}")
                results[provider.name] = False
        
        return results
