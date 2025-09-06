def generate_mock_evidence(claim):
    """
    Generates mock evidence for testing when no real evidence is found
    """
    mock_evidence = []
    
    if "india" in claim.lower() and "china" in claim.lower():
        mock_evidence = [
            {
                'sentence': 'Indian and Chinese officials have been discussing potential high-level meetings to improve bilateral relations.',
                'entailment': 0.4,
                'contradiction': 0.2,
                'neutral': 0.4,
                'source': {
                    'url': 'https://www.reuters.com/world/india-china-talks',
                    'title': 'India-China Diplomatic Discussions - Reuters',
                    'publish_date': '2024-01-15'
                }
            },
            {
                'sentence': 'No official announcement has been made regarding a visit by the Indian Prime Minister to China.',
                'entailment': 0.1,
                'contradiction': 0.6,
                'neutral': 0.3,
                'source': {
                    'url': 'https://www.bbc.com/news/india-china',
                    'title': 'India-China Relations Update - BBC News',
                    'publish_date': '2024-01-10'
                }
            }
        ]
    
    return mock_evidence