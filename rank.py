import logging
from config import MIN_ENTAILMENT_SCORE, MIN_CONTRADICTION_SCORE
from nli import analyze_obvious_claims  # Add this import

logger = logging.getLogger(__name__)

def rank_evidence(claim, articles, analyze_evidence_func):
    """
    Process and rank evidence from articles
    """
    all_evidence = []
    
    # First check for obvious claims
    obvious_evidence = analyze_obvious_claims(claim, "")
    if obvious_evidence:
        logger.info("Found obvious claim evidence")
        return obvious_evidence
    
    # Then process articles
    for article in articles:
        if article and article.get('text'):
            try:
                evidence_items = analyze_evidence_func(claim, article['text'])
                
                for evidence in evidence_items:
                    # Add source information with credibility
                    evidence['source'] = {
                        'url': article['url'],
                        'title': article.get('title', 'No title available'),
                        'publish_date': article.get('publish_date'),
                        'credibility': article.get('credibility', 0.5),
                        'domain': article.get('source_domain', 'Unknown')
                    }
                    all_evidence.append(evidence)
                    
            except Exception as e:
                logger.error(f"Error analyzing evidence: {e}")
                continue
    
    # Add mock evidence if no real evidence found but articles exist
    if not all_evidence and articles:
        all_evidence = generate_mock_evidence(claim, articles)
        for evidence in all_evidence:
            evidence['source'] = {
                'url': articles[0]['url'],
                'title': articles[0].get('title', 'Related News Source'),
                'credibility': articles[0].get('credibility', 0.6)
            }
    
    # Sort by evidence strength and credibility
    all_evidence.sort(key=lambda x: (
        max(x['entailment'], x['contradiction']),
        x['source'].get('credibility', 0.5)
    ), reverse=True)
    
    return all_evidence

def categorize_evidence(evidence_list):
    """
    Categorizes evidence into supporting, contradicting, and neutral based on entailment and contradiction scores.
    Returns three lists: supporting, contradicting, neutral.
    """
    supporting = []
    contradicting = []
    neutral = []
    for evidence in evidence_list:
        if evidence.get('entailment', 0) >= MIN_ENTAILMENT_SCORE:
            supporting.append(evidence)
        elif evidence.get('contradiction', 0) >= MIN_CONTRADICTION_SCORE:
            contradicting.append(evidence)
        else:
            neutral.append(evidence)
    return supporting, contradicting, neutral

def generate_mock_evidence(claim, articles):
    """
    Generates mock evidence items when no real evidence is found.
    """
    mock_evidence = []
    for article in articles:
        mock_evidence.append({
            'sentence': f"No strong evidence found in this article for the claim: '{claim}'.",
            'entailment': 0.33,
            'contradiction': 0.33,
            'neutral': 0.34,
            'source': {
                'url': article.get('url', ''),
                'title': article.get('title', 'Unknown'),
                'publish_date': article.get('publish_date'),
                'credibility': article.get('credibility', 0.5),
                'domain': article.get('source_domain', 'Unknown')
            }
        })
    return mock_evidence