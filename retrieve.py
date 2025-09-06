import logging
import sys
import certifi
import ssl

# Ensure stdout uses UTF-8 encoding for emoji/unicode
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

class SafeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            self.stream.write(msg + self.terminator)
            self.flush()
        except UnicodeEncodeError:
            msg = self.format(record).encode('utf-8', errors='replace').decode('utf-8')
            self.stream.write(msg + self.terminator)
            self.flush()

logging.basicConfig(handlers=[SafeStreamHandler()], level=logging.INFO, force=True)

import requests
import asyncio
import aiohttp
import re
import time
from newspaper import Article, Config
from config import GOOGLE_API_KEY, GOOGLE_CSE_ID, SEARCH_NUM_RESULTS, SEARCH_EXCLUDE_SITES, USER_AGENT, REQUEST_TIMEOUT, NEWSAPI_KEY, CREDIBLE_DOMAINS
from cache import get_search_cache, get_article_cache

logger = logging.getLogger(__name__)

def create_search_query(user_input):
    """
    Creates optimized search query for fact-checking with better name/entity recognition
    """
    # Clean and correct common misspellings
    corrections = {
        'visite': 'visit', 'mister': 'minister', 'prme': 'prime',
        'chek': 'check', 'factchek': 'factcheck', 'goverment': 'government',
        'hollywod': 'hollywood', 'actress': 'actor actress celebrity'
    }

    query = user_input.strip().lower()
    for wrong, correct in corrections.items():
        query = query.replace(wrong, correct)

    # Extract potential names (2+ word sequences that might be names)
    words = query.split()
    name_candidates = []
    for i in range(len(words)-1):
        if len(words[i]) > 2 and len(words[i+1]) > 2:  # Skip short words
            name_candidates.append(f'"{words[i]} {words[i+1]}"')

    # Create multiple search strategies
    base_query = f'"{query}"'

    # Add fact-checking specific terms
    fact_check_terms = 'official confirmed real fake hoax verified'

    # Add current year for recency
    from datetime import datetime
    current_year = datetime.now().year

    # Create comprehensive search query
    if name_candidates:
        # If we detected potential names, search for them specifically
        name_search = ' OR '.join(name_candidates)
        optimized_query = f'({base_query}) OR ({name_search}) {fact_check_terms} {current_year}'
    else:
        optimized_query = f'{base_query} {fact_check_terms} {current_year}'

    return optimized_query

def analyze_source_credibility(url):
    """
    Analyze source credibility score
    """
    try:
        domain = url.split('//')[-1].split('/')[0].lower()
        
        # Check against credible domains
        for credible_domain in CREDIBLE_DOMAINS:
            if credible_domain in domain:
                return 0.9  # Highly credible
        
        # Check for government/edu domains
        if '.gov.' in domain or '.gov/' in domain or '.edu.' in domain or '.ac.' in domain:
            return 0.85
        
        # Check for news domains
        news_keywords = ['news', 'reporter', 'journal', 'times', 'post', 'tribune']
        if any(keyword in domain for keyword in news_keywords):
            return 0.7
        
        return 0.5  # Neutral credibility
        
    except:
        return 0.5

def google_search(query):
    """
    Real Google Search API implementation with retries
    """
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        logger.warning("Google API credentials not configured")
        return None

    url = "https://www.googleapis.com/customsearch/v1"

    # Build query with exclusions
    exclude_str = " ".join([f"-site:{site}" for site in SEARCH_EXCLUDE_SITES])
    full_query = f"{query} {exclude_str}"

    params = {
        'key': GOOGLE_API_KEY,
        'cx': GOOGLE_CSE_ID,
        'q': full_query,
        'num': SEARCH_NUM_RESULTS,
        'dateRestrict': 'm3',  # Past 3 months
        'gl': 'us',
        'lr': 'lang_en'
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"Google search attempt {attempt + 1} for query: {query[:50]}...")
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT, verify=certifi.where())
            response.raise_for_status()
            search_results = response.json()

            urls = []
            for item in search_results.get('items', []):
                link = item['link']
                # Filter out unwanted formats
                if not any(link.lower().endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.ppt']):
                    urls.append(link)

            logger.info(f"Google search successful: found {len(urls)} URLs")
            return urls[:SEARCH_NUM_RESULTS]

        except requests.exceptions.Timeout:
            logger.warning(f"Google search timeout on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:  # Rate limit
                logger.warning(f"Google API rate limit on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(5)
            else:
                logger.error(f"Google search HTTP error: {e}")
                break
        except Exception as e:
            logger.error(f"Google search error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                break

    logger.error("Google search failed after all retries")
    return None

def newsapi_search(query):
    """
    NewsAPI fallback search with retries
    """
    if not NEWSAPI_KEY:
        logger.warning("NewsAPI key not configured")
        return None

    url = "https://newsapi.org/v2/everything"
    params = {
        'q': query,
        'apiKey': NEWSAPI_KEY,
        'pageSize': SEARCH_NUM_RESULTS,
        'sortBy': 'publishedAt',
        'language': 'en',
        'from': '2024-01-01'  # Current year
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"NewsAPI search attempt {attempt + 1} for query: {query[:50]}...")
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT, verify=certifi.where())
            response.raise_for_status()
            data = response.json()

            if data['status'] == 'ok' and data['totalResults'] > 0:
                urls = [article['url'] for article in data['articles']]
                logger.info(f"NewsAPI search successful: found {len(urls)} URLs")
                return urls
            else:
                logger.warning(f"NewsAPI returned no results: {data.get('message', 'Unknown error')}")
                return None

        except requests.exceptions.Timeout:
            logger.warning(f"NewsAPI timeout on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:  # Rate limit
                logger.warning(f"NewsAPI rate limit on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(5)
            elif response.status_code == 401:
                logger.error("NewsAPI authentication failed - check API key")
                break
            else:
                logger.error(f"NewsAPI HTTP error: {e}")
                break
        except Exception as e:
            logger.error(f"NewsAPI error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                break

    logger.error("NewsAPI search failed after all retries")
    return None

def get_fallback_urls(query):
    """
    Smart fallback URLs based on query content with diverse trusted sources
    """
    query_lower = query.lower()

    if any(word in query_lower for word in ['india', 'china', 'modi', 'xi']):
        return [
            "https://www.bbc.com/news/world/asia/india",
            "https://www.aljazeera.com/where/india/",
            "https://www.scmp.com/topics/india-china-relations",
            "https://www.thehindu.com/news/national/",
            "https://indianexpress.com/section/india/",
            "https://www.ndtv.com/india",
            "https://timesofindia.indiatimes.com/india",
            "https://www.dailymail.co.uk/indiahome/index.html"
        ]
    elif any(word in query_lower for word in ['ai', 'artificial', 'robot', 'automation']):
        return [
            "https://www.technologyreview.com/category/ai/",
            "https://www.wired.com/category/ai/",
            "https://www.theverge.com/ai-artificial-intelligence",
            "https://www.nytimes.com/section/technology/ai",
            "https://www.bbc.com/news/technology",
            "https://www.cnet.com/tags/artificial-intelligence/",
            "https://www.zdnet.com/topic/artificial-intelligence/",
            "https://venturebeat.com/ai/"
        ]
    else:
        return [
            "https://www.bbc.com/news",
            "https://www.aljazeera.com/",
            "https://www.theguardian.com/world",
            "https://www.nytimes.com/",
            "https://www.washingtonpost.com/",
            "https://www.cnn.com/",
            "https://www.npr.org/",
            "https://www.reuters.com/"
        ]

def search_web(query):
    """
    Main search function with multiple fallbacks and caching
    """
    optimized_query = create_search_query(query)
    cache = get_search_cache()

    # Force fresh search by skipping cache for better diversity
    # cached_result = cache.get(optimized_query)
    # if cached_result:
    #     logger.info(f"Using cached search results for: {optimized_query[:50]}...")
    #     return cached_result

    logger.info(f"Searching: {optimized_query}")

    all_urls = []

    # 1. Try Google Search
    urls = google_search(optimized_query)
    if urls:
        logger.info(f"Found {len(urls)} URLs via Google Search")
        all_urls.extend(urls)

    # 2. Try NewsAPI
    urls = newsapi_search(optimized_query)
    if urls:
        logger.info(f"Found {len(urls)} URLs via NewsAPI")
        all_urls.extend(urls)

    # 3. Add diverse fallback URLs if we don't have enough sources
    if len(all_urls) < SEARCH_NUM_RESULTS:
        fallback_urls = get_fallback_urls(optimized_query)
        logger.info(f"Adding {len(fallback_urls)} diverse fallback sources")

        # Filter out duplicates and ensure diversity
        existing_domains = {url.split('//')[-1].split('/')[0] for url in all_urls}
        diverse_fallbacks = []

        for url in fallback_urls:
            domain = url.split('//')[-1].split('/')[0]
            if domain not in existing_domains:
                diverse_fallbacks.append(url)
                existing_domains.add(domain)

        all_urls.extend(diverse_fallbacks[:SEARCH_NUM_RESULTS - len(all_urls)])

    # Remove duplicates and limit results
    unique_urls = list(dict.fromkeys(all_urls))[:SEARCH_NUM_RESULTS]

    logger.info(f"Final search results: {len(unique_urls)} diverse URLs from {len(set(url.split('//')[-1].split('/')[0] for url in unique_urls))} sources")

    # Cache the diverse results
    cache.set(optimized_query, unique_urls)
    return unique_urls

async def fetch_article_async(session, url):
    """
    Fetch and parse article with enhanced error handling and caching
    """
    cache = get_article_cache()

    # Check cache first
    cached_article = cache.get(url)
    if cached_article:
        logger.debug(f"Using cached article: {url[:50]}...")
        return cached_article

    try:
        logger.debug(f"Fetching article: {url[:50]}...")
        newspaper_config = Config()
        newspaper_config.browser_user_agent = USER_AGENT
        newspaper_config.request_timeout = REQUEST_TIMEOUT
        newspaper_config.memoize_articles = False

        article = Article(url, config=newspaper_config)

        async with session.get(url, timeout=REQUEST_TIMEOUT,
                             headers={'User-Agent': USER_AGENT}) as response:
            html = await response.text()

        article.download(input_html=html)
        article.parse()

        # Calculate source credibility
        credibility = analyze_source_credibility(url)

        article_data = {
            'url': url,
            'title': article.title,
            'text': article.text,
            'publish_date': article.publish_date,
            'authors': article.authors,
            'top_image': article.top_image,
            'credibility': credibility,
            'source_domain': url.split('//')[-1].split('/')[0]
        }

        # Cache the result
        cache.set(url, article_data)
        logger.debug(f"Cached article: {url[:50]}...")

        return article_data

    except Exception as e:
        # Remove emojis from error message to avoid UnicodeEncodeError in logs
        error_message = str(e)
        for emoji in ['❌', '✅', '🔍', '🤖', '⚠️', '🎯', '📋', '🔐', '💰', '🧪', '🎯', '🛠️', '⚠️', '📊', '📰', '🚨', '🎯']:
            error_message = error_message.replace(emoji, '')
        logger.error(f"Failed to fetch {url}: {error_message}")
        return None

async def fetch_all_articles_async(urls):
    """
    Fetch multiple articles asynchronously
    """
    if not urls:
        return []
    
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(limit=5, ssl=ssl_context)
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = [fetch_article_async(session, url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_results = []
        for result in results:
            if not isinstance(result, Exception) and result is not None:
                successful_results.append(result)
        
        logger.info(f"Successfully fetched {len(successful_results)} articles")
        return successful_results
