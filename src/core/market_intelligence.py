"""
Market Intelligence with Internet-Connected LLM.
For fast mode: Get current market context, news, and sentiment without trading recommendations.
Uses Perplexity AI or web search + OpenAI for real-time context.
"""

import logging
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class MarketIntelligenceLLM:
    """
    LLM with internet access for market context and news.
    Used in fast mode to answer: "What's happening with this token?"
    """
    
    def __init__(self, api_key: Optional[str] = None, provider: str = "perplexity"):
        """
        Initialize market intelligence LLM.
        
        Args:
            api_key: API key for Perplexity or OpenAI
            provider: "perplexity" (recommended) or "openai"
        """
        self.api_key = api_key
        self.provider = provider
        self.enabled = False
        self.client = None
        
        if provider == "perplexity":
            self._init_perplexity()
        elif provider == "openai":
            self._init_openai_with_search()
        else:
            logger.warning(f"Unknown provider: {provider}")
    
    def _init_perplexity(self):
        """Initialize Perplexity AI (designed for web search + reasoning)"""
        try:
            from openai import OpenAI
            
            if not self.api_key:
                from src.core.utils import get_perplexity_api_key
                self.api_key = get_perplexity_api_key()
            
            if not self.api_key:
                # Try using OpenAI key with Perplexity base URL
                from src.core.utils import get_openai_api_key
                self.api_key = get_openai_api_key()
                logger.info("Using OpenAI key - Perplexity requires separate API key for best results")
                logger.info("Get one at: https://www.perplexity.ai/settings/api")
                return
            
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.perplexity.ai"
            )
            self.enabled = True
            logger.info("Market Intelligence LLM initialized with Perplexity AI")
            
        except Exception as e:
            logger.warning(f"Perplexity initialization failed: {e}")
            self.enabled = False
    
    def _init_openai_with_search(self):
        """Fallback: Use OpenAI (doesn't have built-in web search)"""
        try:
            from openai import OpenAI
            from src.core.utils import get_openai_api_key
            
            api_key = self.api_key or get_openai_api_key()
            if not api_key:
                return
            
            self.client = OpenAI(api_key=api_key)
            self.enabled = True
            logger.info("Market Intelligence LLM initialized with OpenAI (no web search)")
            
        except Exception as e:
            logger.warning(f"OpenAI initialization failed: {e}")
            self.enabled = False
    
    def generate_market_intelligence(
        self,
        symbol: str,
        regime_data: Dict,
        features: Dict,
        current_price: Optional[float] = None,
    ) -> str:
        """
        Generate market intelligence report with internet context.
        
        Args:
            symbol: Crypto symbol (e.g., "X:ETHUSD", "X:BTCUSD")
            regime_data: Dict with regime information
            features: Dict with statistical features
            current_price: Current price (optional)
        
        Returns:
            Market intelligence report
        """
        if not self.enabled:
            return self._fallback_intelligence(symbol, regime_data)
        
        # Extract clean symbol for search
        clean_symbol = symbol.replace("X:", "").replace("USD", "")  # ETH, BTC, etc.
        
        # Build comprehensive prompt
        system_prompt = """You are a crypto market analyst with access to real-time information.
        
Provide comprehensive market intelligence covering:
1. Recent news and events (last 7 days)
2. Current market sentiment
3. Major developments or catalysts
4. Technical analysis context
5. Risk factors to watch

Be specific, cite sources when possible, focus on actionable insights."""

        # Build user prompt with regime analysis
        regime_label = regime_data.get('label', 'unknown')
        confidence = regime_data.get('confidence', 0)
        hurst = features.get('hurst_avg', 0.5)
        
        price_context = f"Current price: ${current_price:.2f}" if current_price else "Price data analyzed"
        
        user_prompt = f"""Analyze {clean_symbol} cryptocurrency market intelligence:

**Technical Regime Analysis:**
- Detected Regime: {regime_label} ({confidence:.0%} confidence)
- Hurst Exponent: {hurst:.2f} (trend persistence)
- {price_context}

**What I need:**
1. **Recent News & Events (last 7 days):**
   - Major announcements or developments
   - Regulatory updates
   - Technical upgrades or partnerships
   - Market-moving events

2. **Current Market Sentiment:**
   - Overall crypto market conditions
   - {clean_symbol}-specific sentiment
   - Social media buzz or concerns

3. **Technical Context:**
   - How does the {regime_label} regime align with market conditions?
   - Key support/resistance levels if known
   - Trading volume trends

4. **Risk Factors:**
   - What could change the regime?
   - Upcoming events to watch
   - Broader crypto/macro risks

5. **Bottom Line:**
   - Is now a good time to pay attention to {clean_symbol}?
   - What's the market narrative around it?

Provide a concise but comprehensive market intelligence report (4-5 paragraphs)."""

        try:
            if self.provider == "perplexity":
                return self._generate_perplexity(user_prompt, system_prompt)
            else:
                return self._generate_openai(user_prompt, system_prompt)
        except Exception as e:
            logger.error(f"Market intelligence generation failed: {e}")
            return self._fallback_intelligence(symbol, regime_data)
    
    def generate(self, prompt: str, system_prompt: str = None, max_tokens: int = 1000, temperature: float = 0.6) -> str:
        """
        Generate text using configured provider.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system instruction
            max_tokens: Maximum tokens
            temperature: Sampling temperature
        
        Returns:
            Generated text
        """
        if not self.enabled:
            return ""
        
        try:
            if self.provider == "perplexity":
                return self._generate_perplexity(prompt, system_prompt or "You are a helpful assistant.")
            elif self.provider == "openai":
                return self._generate_openai(prompt, system_prompt or "You are a helpful assistant.")
            return ""
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return ""
    
    def _generate_perplexity(self, user_prompt: str, system_prompt: str) -> str:
        """Generate using Perplexity (has web search built-in)"""
        logger.info("🌐 Generating market intelligence with Perplexity (web search enabled)...")
        
        # Use current Perplexity model (as of Oct 2025)
        # sonar = standard with web search
        # sonar-pro = higher quality with web search
        # sonar-reasoning = advanced reasoning with web search
        
        response = self.client.chat.completions.create(
            model="sonar",  # Standard model with web search and citations
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1000,
            temperature=0.6,
        )
        
        content = response.choices[0].message.content
        
        # Add sources if available
        if hasattr(response, 'citations') and response.citations:
            content += "\n\n**Sources:**\n"
            for citation in response.citations[:5]:  # Top 5 sources
                content += f"- {citation}\n"
        
        logger.info(f"Generated market intelligence ({len(content)} chars)")
        return content
    
    def _generate_openai(self, user_prompt: str, system_prompt: str) -> str:
        """Generate using OpenAI (no web search)"""
        logger.info("🤖 Generating market intelligence with OpenAI (no web search)...")
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1000,
            temperature=0.7,
        )
        
        content = response.choices[0].message.content
        
        # Add disclaimer
        content += "\n\n_Note: Analysis based on training data. For real-time news, use Perplexity API._"
        
        return content
    
    def _fallback_intelligence(self, symbol: str, regime_data: Dict) -> str:
        """Fallback when LLM not available"""
        regime_label = regime_data.get('label', 'unknown')
        confidence = regime_data.get('confidence', 0)
        
        return f"""**Market Intelligence for {symbol}**

**Technical Regime:** {regime_label} ({confidence:.0%} confidence)

_Market intelligence with real-time news requires API access._
- Set PERPLEXITY_API_KEY for web-search enabled analysis
- Or set OPENAI_API_KEY for LLM-based analysis

**Current Analysis:** The technical regime suggests {regime_label} market behavior based on statistical features.

For complete market intelligence with news, sentiment, and events, please configure an API key.
"""


# Singleton
_market_intel_client: Optional[MarketIntelligenceLLM] = None


def get_market_intelligence_client(provider: str = "perplexity") -> MarketIntelligenceLLM:
    """Get or create market intelligence client"""
    global _market_intel_client
    if _market_intel_client is None:
        _market_intel_client = MarketIntelligenceLLM(provider=provider)
    return _market_intel_client

