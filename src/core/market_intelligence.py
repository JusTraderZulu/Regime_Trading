"""
Market Intelligence with Internet-Connected LLM.
For fast mode: Get current market context, news, and sentiment without trading recommendations.
Uses Perplexity AI or web search + OpenAI for real-time context.
"""

import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

ASSET_CLASS_CONTEXT = {
    "CRYPTO": (
        "Highlight protocol upgrades, on-chain flows, ETF activity, regulatory headlines, "
        "exchange/liquidity conditions, and correlations with macro drivers."
    ),
    "FX": (
        "Focus on central bank policy, macro data surprises, cross-asset flows, rate differentials, "
        "positioning, and geopolitical catalysts that move currency pairs."
    ),
    "EQUITY": (
        "Cover earnings reports, guidance changes, buybacks, sector/ETF flows, macro data (rates, CPI), "
        "liquidity conditions, and notable institutional positioning or options activity."
    ),
}


def _default_instrument_label(symbol: str, asset_class: str) -> str:
    """Derive a human-readable instrument label."""
    if asset_class == "CRYPTO":
        label = symbol.replace("X:", "").replace("_", "").upper()
        if label.endswith("USD") and len(label) > 3:
            base = label[:-3]
            return f"{base}/USD"
        return label
    if asset_class == "FX":
        clean = symbol.replace("C:", "").replace("-", "").replace("_", "").upper()
        if len(clean) == 6:
            return f"{clean[:3]}/{clean[3:]}"
        return clean
    return symbol.replace("NYSE:", "").replace("NASDAQ:", "").replace("ARCA:", "")


class MarketIntelligenceLLM:
    """
    LLM with internet access for market context and news.
    Used in fast mode to answer: "What's happening with this instrument?"
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
        asset_class: str = "UNKNOWN",
        instrument_label: Optional[str] = None,
    ) -> str:
        """
        Generate market intelligence report with internet context.
        
        Args:
            symbol: Instrument symbol (internal or QC format)
            regime_data: Dict with regime information
            features: Dict with statistical features
            current_price: Current price (optional)
            asset_class: Asset class string (CRYPTO, FX, EQUITY)
            instrument_label: Optional cleaned label for prompts
        
        Returns:
            Market intelligence report
        """
        if not self.enabled:
            return self._fallback_intelligence(symbol, regime_data, asset_class, instrument_label)
        
        asset_class = (asset_class or "UNKNOWN").upper()
        instrument_label = instrument_label or _default_instrument_label(symbol, asset_class)
        context_instructions = ASSET_CLASS_CONTEXT.get(
            asset_class,
            "Blend macro, positioning, and technical context relevant to this instrument.",
        )
        
        system_prompt = f"""You are a market analyst with access to real-time information.

Asset Class: {asset_class}
Instrument: {instrument_label}

Provide comprehensive market intelligence covering:
1. Recent news and events (last 7 days)
2. Current market sentiment and positioning shifts
3. Major developments or catalysts to track
4. Technical and quantitative context aligned with the detected regime
5. Risk factors that could trigger a regime shift

Context focus: {context_instructions}

Be specific, cite sources when possible, focus on actionable insights."""

        # Build user prompt with regime analysis
        regime_label = regime_data.get('label', 'unknown')
        confidence = regime_data.get('confidence', 0)
        hurst = features.get('hurst_avg', 0.5)
        
        price_context = f"Current price: ${current_price:.2f}" if current_price else "Price data analyzed"
        
        user_prompt = f"""Analyze {instrument_label} market intelligence:

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
   - Overall {asset_class.title()} market conditions
   - {instrument_label} specific sentiment or flows
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
            return self._fallback_intelligence(symbol, regime_data, asset_class, instrument_label)
    
    def generate_trading_guidance(
        self,
        symbol: str,
        regime_label: str,
        confidence: float,
        asset_class: str = "UNKNOWN",
        instrument_label: Optional[str] = None,
    ) -> str:
        """
        Generate concise trading guidance focused on the detected regime.
        """
        if not self.enabled:
            return self._fallback_guidance(symbol, regime_label, confidence, asset_class, instrument_label)

        asset_class = (asset_class or "UNKNOWN").upper()
        instrument_label = instrument_label or _default_instrument_label(symbol, asset_class)
        context_instructions = ASSET_CLASS_CONTEXT.get(
            asset_class,
            "Blend macro, positioning, and technical context relevant to this instrument.",
        )

        system_prompt = f"""You are a disciplined market strategist.

Goal: Provide risk-aware trading guidance grounded in statistical regimes.

Asset Class: {asset_class}
Instrument: {instrument_label}
Confidence: {confidence:.0%}

Key considerations: {context_instructions}

Deliver a succinct three-part answer: Bias & Evidence, Key Levels/Catalysts, and Risk Management."""

        user_prompt = f"""Detected Regime: {regime_label}
Confidence: {confidence:.0%}

Compose trading guidance covering:
1. Bias & Evidence — Position bias (long/short/neutral) and 2-3 supporting datapoints.
2. Key Levels or Catalysts — Levels to watch, upcoming events, or flow triggers.
3. Risk Management — Hedging ideas, invalidation triggers, sizing notes.

Limit the response to ~200 words."""

        try:
            if self.provider == "perplexity":
                return self._generate_perplexity(user_prompt, system_prompt)
            return self._generate_openai(user_prompt, system_prompt)
        except Exception as exc:
            logger.error(f"Trading guidance generation failed: {exc}")
            return self._fallback_guidance(symbol, regime_label, confidence, asset_class, instrument_label)

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
    
    def _fallback_intelligence(
        self,
        symbol: str,
        regime_data: Dict,
        asset_class: str = "UNKNOWN",
        instrument_label: Optional[str] = None,
    ) -> str:
        """Fallback when LLM not available"""
        regime_label = regime_data.get('label', 'unknown')
        confidence = regime_data.get('confidence', 0)
        asset_class = (asset_class or "UNKNOWN").upper()
        instrument_label = instrument_label or _default_instrument_label(symbol, asset_class)
        
        return f"""**Market Intelligence for {instrument_label} ({asset_class})**

**Technical Regime:** {regime_label} ({confidence:.0%} confidence)

_Market intelligence with real-time news requires API access._
- Set PERPLEXITY_API_KEY for web-search enabled analysis
- Or set OPENAI_API_KEY for LLM-based analysis

**Current Analysis:** The technical regime suggests {regime_label} market behavior based on statistical features.

For complete market intelligence with news, sentiment, and events, please configure an API key.
"""

    def _fallback_guidance(
        self,
        symbol: str,
        regime_label: str,
        confidence: float,
        asset_class: str = "UNKNOWN",
        instrument_label: Optional[str] = None,
    ) -> str:
        """Fallback guidance when LLM is unavailable."""
        asset_class = (asset_class or "UNKNOWN").upper()
        instrument_label = instrument_label or _default_instrument_label(symbol, asset_class)

        return f"""**Guidance for {instrument_label} ({asset_class})**

- Detected regime: {regime_label} ({confidence:.0%} confidence)
- Bias: Stay adaptive; no qualitative guidance available without LLM access.
- Action: Monitor quantitative triggers and configure PERPLEXITY_API_KEY for richer guidance."""


# Singleton
_market_intel_client: Optional[MarketIntelligenceLLM] = None


def get_market_intelligence_client(provider: str = "perplexity") -> MarketIntelligenceLLM:
    """Get or create market intelligence client"""
    global _market_intel_client
    if _market_intel_client is None:
        _market_intel_client = MarketIntelligenceLLM(provider=provider)
    return _market_intel_client
