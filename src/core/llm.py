"""
LLM utilities for enhanced report generation.
Supports both OpenAI (preferred) and Hugging Face Inference API.
"""

import logging
import os
from typing import Optional

from langchain_openai import ChatOpenAI

from src.core.utils import get_huggingface_token, get_openai_api_key

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Wrapper for LLM APIs (OpenAI or Hugging Face).
    Prefers OpenAI if available, falls back to HuggingFace.
    """

    DEFAULT_OPENAI_MODEL = "gpt-4o-mini"  # Cost-effective, excellent quality
    DEFAULT_HF_MODEL = "meta-llama/Llama-3.2-3B-Instruct"  # Good quality, fast, free

    def __init__(
        self, openai_key: Optional[str] = None, hf_token: Optional[str] = None, model: Optional[str] = None
    ):
        self.openai_key = openai_key or get_openai_api_key()
        self.hf_token = hf_token or get_huggingface_token()
        self.model = model
        self.provider = None
        self.client = None
        self.enabled = False

        # Try OpenAI first (better quality)
        if self.openai_key:
            self._init_openai()
        # Fallback to Hugging Face
        elif self.hf_token:
            self._init_huggingface()
        else:
            logger.warning("No LLM API key found - LLM features disabled")

    def _init_openai(self):
        """Initialize OpenAI client"""
        try:
            self.model = self.model or self.DEFAULT_OPENAI_MODEL
            self.client = ChatOpenAI(
                model=self.model,
                temperature=0.7,
                api_key=self.openai_key,
            )
            self.provider = "openai"
            self.enabled = True
            logger.info(f"LLM client initialized with OpenAI: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {e}")
            self.enabled = False

    def _init_huggingface(self):
        """Initialize Hugging Face client"""
        try:
            from huggingface_hub import InferenceClient

            self.model = self.model or self.DEFAULT_HF_MODEL
            self.client = InferenceClient(token=self.hf_token)
            self.provider = "huggingface"
            self.enabled = True
            logger.info(f"LLM client initialized with HuggingFace: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize HuggingFace: {e}")
            self.enabled = False

    def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate text using configured LLM API.

        Args:
            prompt: User prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            system_prompt: Optional system instruction

        Returns:
            Generated text
        """
        if not self.enabled:
            logger.warning("LLM not enabled, returning empty string")
            return ""

        try:
            if self.provider == "openai":
                return self._generate_openai(prompt, max_tokens, temperature, system_prompt)
            elif self.provider == "huggingface":
                return self._generate_huggingface(prompt, max_tokens, temperature, system_prompt)
            else:
                return ""
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return ""

    def _generate_openai(
        self, prompt: str, max_tokens: int, temperature: float, system_prompt: Optional[str]
    ) -> str:
        """Generate using OpenAI"""
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        logger.info("🤖 Generating AI analysis with OpenAI...")
        
        response = self.client.invoke(
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        logger.debug(f"OpenAI generated {len(response.content)} chars")
        return response.content.strip()

    def _generate_huggingface(
        self, prompt: str, max_tokens: int, temperature: float, system_prompt: Optional[str]
    ) -> str:
        """Generate using Hugging Face"""
        from tqdm import tqdm
        import sys
        
        # Format prompt for chat models
        if system_prompt:
            full_prompt = f"<s>[INST] {system_prompt}\n\n{prompt} [/INST]"
        else:
            full_prompt = f"<s>[INST] {prompt} [/INST]"

        # Show progress bar while waiting for HF API
        logger.info("🤗 Generating AI analysis with Hugging Face (this may take 30-60 seconds on free tier)...")
        
        with tqdm(total=100, desc="AI Analysis", bar_format='{l_bar}{bar}| {elapsed}', file=sys.stderr) as pbar:
            # Start progress animation
            pbar.update(10)
            
            response = self.client.text_generation(
                full_prompt,
                model=self.model,
                max_new_tokens=max_tokens,
                temperature=temperature,
                return_full_text=False,
            )
            
            pbar.update(90)  # Complete

        logger.debug(f"HuggingFace generated {len(response)} chars")
        return response.strip()

    def generate_regime_summary(
        self,
        symbol: str,
        regime_lt: str,
        regime_mt: str,
        regime_st: str,
        features: dict,
        ccm_notes: Optional[str] = None,
        contradictor_notes: Optional[str] = None,
    ) -> str:
        """
        Generate natural language regime analysis summary.

        Args:
            symbol: Asset symbol
            regime_lt: Long-term regime
            regime_mt: Medium-term regime
            regime_st: Short-term regime
            features: Dict with feature values
            ccm_notes: Cross-asset context notes
            contradictor_notes: Contradictor findings

        Returns:
            Natural language summary
        """
        if not self.enabled:
            return self._fallback_summary(symbol, regime_st)

        system_prompt = """You are a quantitative analyst specializing in crypto market regime analysis.
Provide concise, professional analysis in 2-3 paragraphs. Focus on actionable insights.
Use technical terminology but keep it accessible. Be specific about market conditions."""

        user_prompt = f"""Analyze the following market regime data for {symbol}:

**Multi-Timeframe Regimes:**
- Long-term (1D): {regime_lt}
- Medium-term (4H): {regime_mt}  
- Short-term (15m): {regime_st}

**Key Features:**
- Hurst Exponent (ST): {features.get('hurst_avg', 'N/A'):.2f}
- Variance Ratio (ST): {features.get('vr_statistic', 'N/A'):.2f}
- Volatility (ST): {features.get('returns_vol', 'N/A'):.4f}

**Cross-Asset Context:**
{ccm_notes or 'No cross-asset data available'}

**Contradictor Findings:**
{contradictor_notes or 'No significant contradictions'}

Provide a 2-3 paragraph analysis covering:
1. Current market state and what it means for traders
2. Alignment or divergence across timeframes
3. Key risks and opportunities"""

        return self.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=400,
            temperature=0.6,  # Slightly lower for more factual output
        )

    def _fallback_summary(self, symbol: str, regime_st: str) -> str:
        """Fallback when LLM is not available"""
        return f"Market regime analysis for {symbol}: {regime_st}. LLM summary unavailable - set HUGGINGFACE_API_TOKEN for enhanced reports."


# Singleton instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create LLM client singleton"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client

