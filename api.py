from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import time
import logging
from pydantic import BaseModel
from typing import List, Optional

from retrieve import search_web, fetch_all_articles_async
from nli import analyze_evidence
from rank import rank_evidence, categorize_evidence
from verdict import determine_web_search_verdict, determine_ai_verdict, generate_rationale
from reasoning import should_use_ai_reasoning, generate_ai_reasoning

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom exceptions
class NetworkError(Exception):
    """Raised when network operations fail"""
    pass

class AnalysisError(Exception):
    """Raised when evidence analysis fails"""
    pass

class SearchError(Exception):
    """Raised when search operations fail"""
    pass

class VerdictError(Exception):
    """Raised when verdict determination fails"""
    pass

app = FastAPI(title="Fake News Detector API", version="2.0")

# Add CORS middleware to allow requests from your Streamlit app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development. Restrict in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ClaimRequest(BaseModel):
    claim: str

class EvidenceItem(BaseModel):
    sentence: str
    entailment: float
    contradiction: float
    neutral: float
    source: dict

class VerdictResponse(BaseModel):
    prediction: str
    rationale: str
    evidence: List[EvidenceItem]
    processing_time: float
    articles_processed: int
    ai_reasoning: Optional[str] = None
    web_search_verdict: Optional[str] = None
    web_search_reason: Optional[str] = None
    ai_verdict: Optional[str] = None
    ai_verdict_reason: Optional[str] = None

@app.post("/check", response_model=VerdictResponse)
async def check_claim(request: ClaimRequest):
    start_time = time.time()
    ai_reasoning = None

    try:
        logger.info(f"Processing claim: {request.claim[:100]}...")

        # 1. Search for the claim
        try:
            logger.info("Searching for relevant sources...")
            urls = search_web(request.claim)
            if not urls:
                logger.warning("No URLs found for claim")
                # Generate AI reasoning when no URLs are found
                ai_reasoning = generate_ai_reasoning(request.claim, [], "UNCLEAR", "No relevant sources found for this claim.")
                return VerdictResponse(
                    prediction="UNCLEAR",
                    rationale=f"No relevant sources found for this claim.\n\nAI Analysis: {ai_reasoning}" if ai_reasoning else "No relevant sources found for this claim.",
                    evidence=[],
                    processing_time=time.time() - start_time,
                    articles_processed=0,
                    ai_reasoning=ai_reasoning
                )
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise SearchError(f"Failed to search for claim: {str(e)}")

        # 2. Fetch and parse articles asynchronously
        try:
            logger.info(f"Fetching {len(urls)} articles...")
            articles = await fetch_all_articles_async(urls)
            logger.info(f"Successfully fetched {len(articles)} articles")
        except Exception as e:
            logger.error(f"Article fetching failed: {str(e)}")
            raise NetworkError(f"Failed to fetch articles: {str(e)}")

        # 3. Analyze evidence from all articles
        try:
            logger.info("Analyzing evidence...")
            all_evidence = rank_evidence(request.claim, articles, analyze_evidence)
            logger.info(f"Found {len(all_evidence)} total evidence sentences")
        except Exception as e:
            logger.error(f"Evidence analysis failed: {str(e)}")
            raise AnalysisError(f"Failed to analyze evidence: {str(e)}")

        # 4. Categorize evidence and determine verdicts
        try:
            supporting, contradicting, neutral = categorize_evidence(all_evidence)
            logger.info(f"Evidence categorized - Supporting: {len(supporting)}, Contradicting: {len(contradicting)}, Neutral: {len(neutral)}")

            # Generate web search verdict
            web_search_verdict, web_search_reason = determine_web_search_verdict(supporting, contradicting, neutral)

            # Generate AI verdict
            ai_verdict, ai_verdict_reason = determine_ai_verdict(request.claim, articles)

            # Use web search verdict as the main prediction for backward compatibility
            verdict = web_search_verdict
            verdict_reason = web_search_reason

        except Exception as e:
            logger.error(f"Verdict determination failed: {str(e)}")
            raise VerdictError(f"Failed to determine verdict: {str(e)}")

        # 5. Generate additional AI reasoning if needed
        try:
            if should_use_ai_reasoning(verdict, supporting, contradicting, articles):
                logger.info("Generating AI reasoning...")
                ai_reasoning = generate_ai_reasoning(request.claim, articles, verdict, verdict_reason)
        except Exception as e:
            logger.warning(f"AI reasoning failed: {str(e)}")
            # Continue without AI reasoning

        rationale = generate_rationale((verdict, verdict_reason), supporting, contradicting)

        # Add AI reasoning to rationale if available
        if ai_reasoning:
            rationale += f"\n\nAI Analysis: {ai_reasoning}"

        # Combine all evidence for response
        combined_evidence = supporting + contradicting + neutral

        logger.info(f"Returning {len(combined_evidence)} evidence items")
        logger.debug(f"Verdict: {verdict}, Processing time: {time.time() - start_time:.2f}s")

        return VerdictResponse(
            prediction=verdict,
            rationale=rationale,
            evidence=combined_evidence[:10],  # Return top 10 evidence items
            processing_time=time.time() - start_time,
            articles_processed=len(articles),
            ai_reasoning=ai_reasoning,
            web_search_verdict=web_search_verdict,
            web_search_reason=web_search_reason,
            ai_verdict=ai_verdict,
            ai_verdict_reason=ai_verdict_reason
        )

    except SearchError as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Search service unavailable: {str(e)}")
    except NetworkError as e:
        logger.error(f"Network error: {str(e)}")
        raise HTTPException(status_code=502, detail=f"Network error: {str(e)}")
    except AnalysisError as e:
        logger.error(f"Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    except VerdictError as e:
        logger.error(f"Verdict error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Verdict determination failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in check_claim: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Fake News Detector API is running!", "version": "2.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
