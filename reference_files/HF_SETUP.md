# 🤗 Hugging Face Setup Guide

## Get Your Free API Token

1. Go to https://huggingface.co/settings/tokens
2. Click **"Create new token"**
3. Name it: `regime-detector`
4. Type: **Read** (free tier)
5. Click **"Create token"**
6. **Copy the token** (starts with `hf_...`)

## Add to Your Project

Open your `.env` file and add:

```bash
HUGGINGFACE_API_TOKEN=hf_your_token_here
```

## Test It!

Run XRP analysis again - it will now include AI-enhanced commentary:

```bash
python -m src.ui.cli run --symbol X:XRPUSD --mode fast
```

Look for the new **"AI-Enhanced Analysis"** section in the report!

## Models Used

**Default**: `mistralai/Mistral-7B-Instruct-v0.2` (Free tier, great for financial analysis)

**Alternatives** (can change in `src/core/llm.py`):
- `google/gemma-7b-it` (Good for structured output)
- `HuggingFaceH4/zephyr-7b-beta` (Strong instruction following)
- `meta-llama/Meta-Llama-3-8B-Instruct` (Requires HF Pro)

## Features

With LLM enabled, you get:

✅ Natural language regime analysis  
✅ Market context and implications  
✅ Risk assessment and opportunities  
✅ Multi-timeframe fusion insights  
✅ Actionable trading commentary  

## Free Tier Limits

- **1,000 requests/day** per token
- **30 requests/hour** burst
- Plenty for regime analysis! 🎉

## Fallback

If no token or rate limit hit, system falls back to template-based reports (original behavior).

