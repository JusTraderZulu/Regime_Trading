"""
Market Context Parser
Extracts structured facts and impact scores from LLM market context output.
"""

import logging
import re
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


def parse_context_output(llm_text: str) -> Tuple[List[Dict], str]:
    """
    Parse LLM output into structured facts and narrative.
    
    Expected format:
    STRUCTURED_CONTEXT:
    - [Category] Event (Impact: +3, Source: ...)
    - [Category] Event (Impact: -2, Source: ...)
    
    NARRATIVE:
    [narrative text]
    
    Returns:
        (structured_items, narrative_text)
    """
    if not llm_text:
        return [], ""
    
    # Split into structured and narrative sections
    structured_section = ""
    narrative_section = ""
    
    if "STRUCTURED_CONTEXT:" in llm_text:
        parts = llm_text.split("NARRATIVE:")
        structured_section = parts[0].replace("STRUCTURED_CONTEXT:", "").strip()
        narrative_section = parts[1].strip() if len(parts) > 1 else llm_text
    else:
        # Fallback: entire text is narrative
        narrative_section = llm_text
    
    # Parse structured items
    items = []
    if structured_section:
        for line in structured_section.split('\n'):
            line = line.strip()
            if not line or not line.startswith('-'):
                continue
            
            item = _parse_context_line(line)
            if item:
                items.append(item)
    
    return items, narrative_section


def _parse_context_line(line: str) -> Dict:
    """
    Parse a single context item line.
    
    Format: - [Category] Event description (Impact: +3, Source: Bloomberg, Date: Oct 22)
    """
    # Extract category
    category_match = re.search(r'\[([^\]]+)\]', line)
    category = category_match.group(1) if category_match else "General"
    
    # Extract impact score
    impact_match = re.search(r'Impact:\s*([+-]?\d+)', line)
    impact = int(impact_match.group(1)) if impact_match else 0
    
    # Extract source
    source_match = re.search(r'Source:\s*([^,\)]+)', line)
    source = source_match.group(1).strip() if source_match else None
    
    # Extract date
    date_match = re.search(r'Date:\s*([^,\)]+)', line)
    date = date_match.group(1).strip() if date_match else None
    
    # Event is everything after category, before (Impact:...)
    event = line
    if category_match:
        event = line[category_match.end():].strip()
    event = re.sub(r'\(Impact:.*?\)', '', event).strip()
    event = event.lstrip('- ').strip()
    
    return {
        'category': category,
        'event': event,
        'impact_raw': impact,
        'source': source,
        'date': date
    }


def calculate_context_nudge(items: List[Dict], cap: float = 0.02) -> float:
    """
    Calculate aggregate impact nudge from context items.
    
    Impact scores are normalized and capped:
    - Raw scores: -5 to +5
    - Normalized: divided by 100 to get -0.05 to +0.05
    - Aggregate: sum of all items
    - Capped: hard limit at ±cap (default 0.02)
    
    Args:
        items: List of context items with 'impact_raw' field
        cap: Maximum absolute nudge (default 0.02)
        
    Returns:
        Nudge value [-cap, +cap]
    """
    if not items:
        return 0.0
    
    # Sum normalized impacts
    total_impact = sum(item.get('impact_raw', 0) for item in items)
    
    # Normalize (divide by 100)
    nudge = total_impact / 100.0
    
    # Cap
    nudge = max(-cap, min(cap, nudge))
    
    logger.info(f"Context nudge: {len(items)} items, total impact {total_impact}, nudge {nudge:+.3f}")
    
    return float(nudge)


def categorize_and_score_items(items: List[Dict]) -> Dict:
    """
    Organize items by category and calculate category-level stats.
    
    Returns:
        Dict with counts and impact by category
    """
    categories = {}
    
    for item in items:
        cat = item.get('category', 'General')
        if cat not in categories:
            categories[cat] = {
                'count': 0,
                'total_impact': 0,
                'items': []
            }
        
        categories[cat]['count'] += 1
        categories[cat]['total_impact'] += item.get('impact_raw', 0)
        categories[cat]['items'].append(item)
    
    return categories

