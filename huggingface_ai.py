import requests
import time
import logging
import os
from config import HUGGINGFACE_API_KEY, HUGGINGFACE_MODEL

logger = logging.getLogger(__name__)

# Google Gemini API configuration (free tier available)
from config import GEMINI_API_KEY
try:
    import google.generativeai as genai
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("Gemini AI model initialized successfully")
    else:
        gemini_model = None
        logger.warning("GEMINI_API_KEY not configured")
except ImportError:
    logger.warning("Google Generative AI library not installed")
    gemini_model = None

def create_ai_prompt(claim, articles, verdict, rationale):
    """
    Create conversational AI prompt similar to ChatGPT/Grok style responses
    """
    # Prepare article context
    article_context = ""
    if articles:
        article_context = "\n## Articles Found:\n"
        for i, article in enumerate(articles[:3], 1):
            title = article.get('title', 'No title')[:80] + '...' if len(article.get('title', '')) > 80 else article.get('title', 'No title')
            domain = article.get('source_domain', 'Unknown')
            credibility = article.get('credibility', 0.5)
            article_context += f"{i}. **{title}** from {domain} (Credibility: {credibility:.1f}/1.0)\n"

    # Analyze claim characteristics for better fake detection
    claim_lower = claim.lower()
    suspicious_indicators = []

    # Check for obvious fake indicators
    if 'hollywood' in claim_lower or 'actress' in claim_lower:
        suspicious_indicators.append("Entertainment claim - requires verification from entertainment industry sources")

    # Check for misspelled names (common in fake news)
    words = claim.split()
    for word in words:
        if len(word) > 6 and word.isalpha():  # Long words that might be names
            # Simple heuristic: if word has unusual letter combinations
            if sum(1 for c in word.lower() if c in 'qxyzj') > 2:  # Unusual letters
                suspicious_indicators.append(f"Potentially misspelled or fabricated name: '{word}'")

    suspicious_text = "\n".join(f"- {ind}" for ind in suspicious_indicators) if suspicious_indicators else "None detected"

    return f"""You are an expert fact-checking AI analyst, similar to how ChatGPT or Grok would respond to complex queries. Provide a detailed, conversational analysis of this claim.

## Claim to Analyze:
"{claim}"

## Current Assessment:
- Initial Verdict: {verdict}
- Reasoning: {rationale}

## Suspicious Indicators:
{suspicious_text}

{article_context}

## Your Analysis:

Please provide a comprehensive analysis in a natural, conversational style like other AI assistants would. Cover:

1. **Claim Breakdown**: What exactly is being claimed and why it matters?

2. **Evidence Analysis**: Based on the articles found, what supporting or contradicting evidence exists?

3. **Credibility Assessment**: How reliable are the sources? Are there any red flags?

4. **Context and Background**: What do we know about similar claims or the topic in general?

5. **Verification Challenges**: What makes this claim hard or easy to verify?

6. **Probability Assessment**: Based on everything, how likely is this claim to be true?

7. **Recommendation**: Should this be considered TRUE, FALSE, or UNCLEAR? Why?

Be thorough but conversational - explain your reasoning step by step, acknowledge uncertainties, and provide specific examples or analogies when helpful. Don't just give a verdict; walk through your thought process like a human expert would.

If the claim seems suspicious or fabricated, explain specifically why and what evidence would be needed to prove it true."""

def huggingface_analysis(claim, articles, verdict, rationale):
    """
    Enhanced AI analysis using Google Gemini API for better reasoning
    """
    if not gemini_model:
        logger.warning("Gemini model not available, falling back to Hugging Face")
        return huggingface_fallback_analysis(claim, articles, verdict, rationale)

    prompt = create_ai_prompt(claim, articles, verdict, rationale)

    try:
        response = gemini_model.generate_content(prompt)
        generated_text = response.text.strip()

        if generated_text and len(generated_text) > 100:
            return f"AI FACT-CHECK ANALYSIS:\n\n{generated_text}"

        return generate_fallback_reasoning(claim, articles, verdict)

    except Exception as e:
        logger.error(f"Gemini AI Analysis failed: {e}")
        return huggingface_fallback_analysis(claim, articles, verdict, rationale)

def huggingface_fallback_analysis(claim, articles, verdict, rationale):
    """
    Fallback to Hugging Face if Gemini is not available
    """
    if not HUGGINGFACE_API_KEY:
        return generate_fallback_reasoning(claim, articles, verdict)

    API_URL = f"https://api-inference.huggingface.co/models/{HUGGINGFACE_MODEL}"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}

    prompt = create_ai_prompt(claim, articles, verdict, rationale)

    try:
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_length": 600,
                "temperature": 0.7,
                "do_sample": True,
                "return_full_text": False,
                "top_p": 0.9,
                "repetition_penalty": 1.1
            }
        }

        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)

        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                generated_text = result[0].get('generated_text', '').strip()
                if generated_text and len(generated_text) > 150:
                    return f"AI FACT-CHECK ANALYSIS:\n\n{generated_text}"

        # Handle model loading
        if response.status_code == 503:
            time.sleep(20)
            response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    generated_text = result[0].get('generated_text', '').strip()
                    if generated_text and len(generated_text) > 150:
                        return f"AI FACT-CHECK ANALYSIS:\n\n{generated_text}"

        return generate_fallback_reasoning(claim, articles, verdict)

    except Exception as e:
        logger.error(f"Hugging Face AI Analysis failed: {e}")
        return generate_fallback_reasoning(claim, articles, verdict)

def generate_fallback_reasoning(claim, articles, verdict):
    """
    High-quality fallback reasoning
    """
    reasoning = "**EXPERT ANALYSIS:**\n\n"
    claim_lower = claim.lower()
    
    # Context-specific analysis
    if any(word in claim_lower for word in ['india', 'china', 'modi', 'xi', 'visit', 'diplomacy']):
        reasoning += "• **Diplomatic Claim Analysis**: This involves international relations between India and China\n"
        reasoning += "• **Verification Challenge**: Diplomatic visits require official government confirmation\n"
        reasoning += "• **Credible Sources**: Check Indian MEA, Chinese Foreign Ministry, Reuters, AP\n"
        reasoning += "• **Typical Pattern**: Such announcements come through official press releases\n\n"
        
    elif any(word in claim_lower for word in ['ai', 'artificial', 'job', 'employment']):
        reasoning += "• **Technology Impact Claim**: Involves AI's effect on employment\n"
        reasoning += "• **Verification Approach**: Requires data from research firms and academic studies\n"
        reasoning += "• **Best Sources**: Gartner, McKinsey, World Economic Forum, university research\n"
        reasoning += "• **Complexity**: These claims often have nuanced, sector-specific truths\n\n"
    
    # Add article context
    if articles:
        reasoning += f"• **Content Analyzed**: Reviewed {len(articles)} related articles\n"
        reasoning += "• **Finding**: Articles provide context but not definitive confirmation\n\n"
    else:
        reasoning += "• **Data Availability**: Limited immediate sources found for this specific claim\n\n"
    
    reasoning += "**VERIFICATION STRATEGY**:\n"
    reasoning += "1. **Primary Sources**: Check official government/company statements\n"
    reasoning += "2. **Research Data**: Consult academic studies and industry reports\n"
    reasoning += "3. **Multiple Corroboration**: Require confirmation from 2+ reliable sources\n"
    reasoning += "4. **Temporal Context**: Consider when this information would typically be announced\n"
    reasoning += "5. **Expert Consensus**: Look for agreement among subject matter experts\n"
    
    return reasoning

def test_huggingface_connection():
    """Test Hugging Face connection"""
    if not HUGGINGFACE_API_KEY:
        logger.warning("Hugging Face API key not configured")
        return False

    try:
        test_prompt = "Test fact-checking analysis capability. Respond with 'Operational' if working."
        API_URL = f"https://api-inference.huggingface.co/models/{HUGGINGFACE_MODEL}"
        headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}

        response = requests.post(API_URL, headers=headers,
                               json={"inputs": test_prompt},
                               timeout=30)

        if response.status_code == 200:
            logger.info("Hugging Face API operational")
            return True
        else:
            logger.error(f"Hugging Face API error: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"Hugging Face connection failed: {e}")
        return False

if __name__ == "__main__":
    test_huggingface_connection()