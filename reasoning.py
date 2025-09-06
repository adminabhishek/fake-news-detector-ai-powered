import logging
from config import ENABLE_AI_REASONING, MIN_ARTICLES_FOR_REASONING
from huggingface_ai import huggingface_analysis

logger = logging.getLogger(__name__)

def generate_ai_reasoning(claim, articles, verdict, rationale):
    """
    Main AI reasoning function
    """
    if not ENABLE_AI_REASONING:
        from huggingface_ai import generate_fallback_reasoning
        return generate_fallback_reasoning(claim, articles, verdict)
    
    logger.info(f"Generating AI reasoning for verdict: {verdict}")
    return huggingface_analysis(claim, articles, verdict, rationale)

def should_use_ai_reasoning(verdict, supporting_evidence, contradicting_evidence, articles):
    """
    Determine when to use AI reasoning
    """
    if not ENABLE_AI_REASONING:
        return False
        
    # Use AI for unclear verdicts with some context
    if verdict == "UNCLEAR" and len(articles) >= MIN_ARTICLES_FOR_REASONING:
        return True
        
    # Use AI when evidence is limited but articles exist
    if len(supporting_evidence) + len(contradicting_evidence) < 3 and len(articles) > 0:
        return True
        
    return False
