# Fake News Detection System Improvements - TODO

## 1. Improve Error Handling Across All Modules
- [x] Add specific exception types in api.py (NetworkError, AnalysisError, etc.)
- [x] Enhance error handling in retrieve.py with retries for search APIs
- [x] Add robust error handling in nli.py for model loading and inference
- [x] Improve error handling in rank.py for evidence processing
- [x] Add better error handling in huggingface_ai.py with exponential backoff
- [x] Add error handling in verdict.py for edge cases
- [x] Add error handling in reasoning.py for AI calls

## 2. Add Caching for Search Results and Articles
- [x] Create cache.py module with TTL-based caching
- [x] Add caching to retrieve.py for search results (Google, NewsAPI)
- [x] Add caching to retrieve.py for article fetches
- [x] Update config.py with cache settings (TTL, max size)
- [x] Add cache invalidation logic

## 3. Add Comprehensive Logging
- [x] Configure logging in config.py (file and console handlers)
- [x] Replace print statements with logging in api.py
- [x] Add logging to retrieve.py for search and fetch operations
- [x] Add logging to nli.py for model operations
- [x] Add logging to rank.py for evidence processing
- [x] Add logging to huggingface_ai.py for API calls
- [x] Add logging to verdict.py and reasoning.py

## 4. Separate Web Search and AI Analysis Answers
- [x] Modify API response to include separate web_search_verdict and ai_verdict
- [x] Update verdict.py to generate web-based verdict without AI influence
- [x] Create separate AI verdict generation function
- [x] Update streamlit_app.py to display both verdicts separately
- [x] Modify response model in api.py to include both verdict types
- [x] Test the separate verdict display functionality

## Follow-up Steps
- [ ] Test error handling with simulated failures
- [ ] Test caching performance improvements
- [ ] Verify logging output and levels
- [ ] Update requirements.txt if needed for caching dependencies
- [ ] Create unit tests for improved modules
- [ ] Update documentation with new features
