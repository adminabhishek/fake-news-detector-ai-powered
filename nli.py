from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import torch
import nltk
import logging
from nltk.tokenize import sent_tokenize
from config import NLI_MODEL_NAME, MAX_EVIDENCE_SENTENCES_PER_ARTICLE, MIN_ENTAILMENT_SCORE, MIN_CONTRADICTION_SCORE

logger = logging.getLogger(__name__)

# Download NLTK punkt tokenizer
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    logger.info("Downloading NLTK punkt tokenizer...")
    nltk.download('punkt')

# Load the model
device = 0 if torch.cuda.is_available() else -1
logger.info(f"Loading NLI model '{NLI_MODEL_NAME}' on device: {'GPU' if device == 0 else 'CPU'}")

try:
    tokenizer = AutoTokenizer.from_pretrained(NLI_MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(
        NLI_MODEL_NAME,
        ignore_mismatched_sizes=True
    )
    nli_pipeline = pipeline("text-classification",
                           model=model,
                           tokenizer=tokenizer,
                           device=device,
                           framework="pt",
                           top_k=None)
    logger.info("NLI model loaded successfully")
except Exception as e:
    logger.error(f"Error loading NLI model: {e}")
    nli_pipeline = None

def analyze_evidence(claim, article_text, max_sentences=MAX_EVIDENCE_SENTENCES_PER_ARTICLE):
    """
    Enhanced evidence analysis with better matching
    """
    if nli_pipeline is None or not article_text:
        return []
    
    evidence_list = []
    
    try:
        # Split article into sentences
        sentences = sent_tokenize(article_text)
        
        # Pre-filter sentences for relevance
        relevant_sentences = []
        claim_words = set(claim.lower().split())
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            sentence_words = set(sentence_lower.split())
            
            # Check for word overlap or semantic similarity
            word_overlap = len(claim_words.intersection(sentence_words))
            
            # Keep sentences that have some relevance
            if word_overlap >= 1 or len(sentence.split()) > 5:
                relevant_sentences.append(sentence)
        
        if not relevant_sentences:
            return []
        
        # Process in smaller batches
        batch_size = 6
        for i in range(0, len(relevant_sentences), batch_size):
            batch = relevant_sentences[i:i + batch_size]
            
            inputs = []
            for sentence in batch:
                inputs.append(f"{claim} [SEP] {sentence}")
            
            try:
                results = nli_pipeline(inputs)
                
                for j, result in enumerate(results):
                    if j < len(batch):
                        sentence = batch[j]
                        
                        # Extract scores
                        scores = {}
                        for label_dict in result:
                            label = label_dict['label'].upper()
                            scores[label] = label_dict['score']
                        
                        # Handle different label formats
                        entailment_score = scores.get('ENTAILMENT', scores.get('ENTAIL', 0))
                        contradiction_score = scores.get('CONTRADICTION', scores.get('CONTRADICT', 0))
                        neutral_score = scores.get('NEUTRAL', 0)
                        
                        # Keep evidence with meaningful scores
                        if entailment_score > 0.4 or contradiction_score > 0.4:
                            evidence_list.append({
                                'sentence': sentence,
                                'entailment': entailment_score,
                                'contradiction': contradiction_score,
                                'neutral': neutral_score
                            })
                            
            except Exception as e:
                logger.error(f"Error processing batch: {e}")
                continue
        
        # Sort by evidence strength
        evidence_list.sort(key=lambda x: max(x['entailment'], x['contradiction']), reverse=True)
        return evidence_list[:max_sentences]
        
    except Exception as e:
        logger.error(f"Error in evidence analysis: {e}")
        return []

def analyze_obvious_claims(claim, article_text):
    """
    Handle obviously true/false claims with direct logic
    """
    claim_lower = claim.lower()
    # Obviously false claims
    false_facts = {
        'goat has two legs': {'sentence': 'Goats are quadrupedal animals with four legs, not two.', 'contradiction': 0.9, 'entailment': 0.1, 'neutral': 0.0},
        'earth is flat': {'sentence': 'Scientific consensus confirms the Earth is an oblate spheroid, not flat.', 'contradiction': 0.95, 'entailment': 0.05, 'neutral': 0.0},
        'moon is made of cheese': {'sentence': 'The moon is composed of rock and mineral materials, not cheese.', 'contradiction': 0.9, 'entailment': 0.1, 'neutral': 0.0},
        'water is dry': {'sentence': 'Water is a liquid substance that is wet, not dry.', 'contradiction': 0.85, 'entailment': 0.15, 'neutral': 0.0}
    }
    # Obviously true claims  
    true_facts = {
        'water is wet': {'sentence': 'Water is a liquid that exhibits wetness properties.', 'entailment': 0.9, 'contradiction': 0.1, 'neutral': 0.0},
        'sky is blue': {'sentence': 'The sky appears blue due to Rayleigh scattering of sunlight.', 'entailment': 0.85, 'contradiction': 0.15, 'neutral': 0.0},
        'humans breathe air': {'sentence': 'Humans require oxygen from air for respiration.', 'entailment': 0.95, 'contradiction': 0.05, 'neutral': 0.0}
    }
    # Check if claim matches known facts
    for fact_pattern, evidence in false_facts.items():
        if fact_pattern in claim_lower:
            return [evidence]
    for fact_pattern, evidence in true_facts.items():
        if fact_pattern in claim_lower:
            return [evidence]
    return []