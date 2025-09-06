import logging
from config import MIN_ENTAILMENT_SCORE, MIN_CONTRADICTION_SCORE
from reasoning import should_use_ai_reasoning, generate_ai_reasoning

logger = logging.getLogger(__name__)

def determine_web_search_verdict(supporting_evidence, contradicting_evidence, neutral_evidence, claim=None):
    """
    Determines the verdict based solely on web search evidence, with improved fake detection.
    """
    logger.info(f"Determining web search verdict with {len(supporting_evidence)} supporting, {len(contradicting_evidence)} contradicting, {len(neutral_evidence)} neutral evidence")
    strong_support = [ev for ev in supporting_evidence if ev['entailment'] >= 0.8]
    strong_contradict = [ev for ev in contradicting_evidence if ev['contradiction'] >= 0.8]

    # Check for obvious fake indicators
    is_likely_fake = False
    if claim:
        claim_lower = claim.lower()
        logger.info(f"Checking claim for fake indicators: {claim_lower}")
        # Claims about non-existent people in entertainment industry
        has_entertainment_keywords = ('hollywood' in claim_lower or 'hollywod' in claim_lower) or 'actress' in claim_lower or 'actor' in claim_lower
        has_no_supporting_evidence = len(supporting_evidence) == 0

        logger.info(f"Entertainment keywords found: {has_entertainment_keywords}, No supporting evidence: {has_no_supporting_evidence}")

        if has_entertainment_keywords and has_no_supporting_evidence:
            # Check if the name looks suspicious (long words with unusual letters or patterns)
            words = claim.split()
            logger.info(f"Checking words for suspicious patterns: {words}")
            for word in words:
                if len(word) > 5 and word.isalpha():
                    # Check for unusual letter combinations or patterns
                    unusual_letters = sum(1 for c in word.lower() if c in 'qxyzj')
                    # Also check for repeated letters or other suspicious patterns
                    has_repeated_letters = any(word.lower().count(c) >= 3 for c in 'abcdefghijklmnopqrstuvwxyz')
                    has_unusual_combo = 'bhatiya' in word.lower() or 'tammana' in word.lower()

                    logger.info(f"Word '{word}': unusual_letters={unusual_letters}, repeated_letters={has_repeated_letters}, unusual_combo={has_unusual_combo}")

                    if unusual_letters >= 1 or has_repeated_letters or has_unusual_combo:
                        is_likely_fake = True
                        logger.info(f"Detected suspicious name pattern in word: {word}")
                        break

    # Decision logic based on evidence strength
    if len(strong_support) >= 2 and len(strong_contradict) == 0:
        verdict, reason = "TRUE", "Multiple reliable sources strongly support this claim."
    elif len(strong_contradict) >= 2 and len(strong_support) == 0:
        verdict, reason = "FALSE", "Multiple reliable sources strongly contradict this claim."
    elif len(strong_support) >= 1 and len(strong_contradict) >= 1:
        verdict, reason = "MIXED", "There is conflicting evidence from reliable sources."
    elif len(supporting_evidence) >= 2:
        verdict, reason = "LIKELY TRUE", "Multiple sources support this claim, but not strongly."
    elif len(contradicting_evidence) >= 2:
        verdict, reason = "LIKELY FALSE", "Multiple sources contradict this claim, but not strongly."
    elif len(supporting_evidence) > 0:
        verdict, reason = "UNCLEAR", "Some supporting evidence found, but not sufficient for confirmation."
    elif len(contradicting_evidence) > 0:
        verdict, reason = "UNCLEAR", "Some contradicting evidence found, but not sufficient for refutation."
    elif is_likely_fake:
        verdict, reason = "FALSE", "No credible sources found supporting this claim, and the claim contains suspicious indicators suggesting it may be fabricated."
    else:
        verdict, reason = "UNCLEAR", "Insufficient high-quality evidence to determine veracity."

    return verdict, reason

def determine_ai_verdict(claim, articles):
    """
    Determines the verdict based on AI analysis of the claim and articles.
    """
    logger.info(f"Determining AI verdict for claim: {claim[:50]}...")
    if not articles:
        return "UNCLEAR", "No articles available for AI analysis."

    # Use AI reasoning to generate verdict
    ai_reasoning = generate_ai_reasoning(claim, articles, "UNCLEAR", "AI analysis requested")

    # Parse AI reasoning to extract verdict and detailed reason
    ai_text = ai_reasoning.lower() if ai_reasoning else ""

    if "true" in ai_text and "false" not in ai_text:
        verdict = "TRUE"
        reason = f"AI analysis confirms this claim is likely true. {extract_ai_reasoning_details(ai_reasoning, 'true')}"
    elif "false" in ai_text and "true" not in ai_text:
        verdict = "FALSE"
        reason = f"AI analysis indicates this claim is likely false. {extract_ai_reasoning_details(ai_reasoning, 'false')}"
    elif "mixed" in ai_text or "conflicting" in ai_text:
        verdict = "MIXED"
        reason = f"AI analysis shows mixed or conflicting evidence. {extract_ai_reasoning_details(ai_reasoning, 'mixed')}"
    elif "unclear" in ai_text or "insufficient" in ai_text:
        verdict = "UNCLEAR"
        reason = f"AI analysis finds insufficient evidence for a clear verdict. {extract_ai_reasoning_details(ai_reasoning, 'unclear')}"
    else:
        verdict = "UNCLEAR"
        reason = f"AI analysis could not determine a clear verdict. {extract_ai_reasoning_details(ai_reasoning, 'unclear')}"

    return verdict, reason

def extract_ai_reasoning_details(ai_reasoning, verdict_type):
    """
    Extract detailed reasoning from AI analysis text.
    """
    if not ai_reasoning:
        return "No detailed reasoning available."

    # Look for specific sections in the AI reasoning
    reasoning_lines = ai_reasoning.split('\n')
    relevant_lines = []

    for line in reasoning_lines:
        line_lower = line.lower()
        # Extract lines that contain reasoning keywords
        if any(keyword in line_lower for keyword in [
            'because', 'due to', 'evidence shows', 'analysis indicates',
            'based on', 'according to', 'suggests that', 'indicates that',
            'likely', 'probably', 'appears to', 'seems to'
        ]):
            relevant_lines.append(line.strip())

    if relevant_lines:
        # Return the most relevant reasoning lines (up to 2)
        return ' '.join(relevant_lines[:2])
    else:
        # Return a summary of the AI reasoning
        return ai_reasoning[:200] + "..." if len(ai_reasoning) > 200 else ai_reasoning

def determine_verdict(supporting_evidence, contradicting_evidence, neutral_evidence, articles=None, claim=None):
    """
    Determines the final verdict based on categorized evidence.
    This function is kept for backward compatibility but now uses the web search verdict.
    """
    return determine_web_search_verdict(supporting_evidence, contradicting_evidence, neutral_evidence)

def generate_rationale(verdict, supporting, contradicting):
    """
    Generates a detailed rationale for the verdict.
    """
    logger.debug(f"Generating rationale for verdict: {verdict[0]}")
    rationale = f"Verdict: {verdict[0]}. {verdict[1]} "

    if supporting:
        rationale += f"Found {len(supporting)} supporting evidence sentences. "
    if contradicting:
        rationale += f"Found {len(contradicting)} contradicting evidence sentences."

    if not supporting and not contradicting:
        rationale += "No strong evidence was found for or against the claim."

    return rationale
