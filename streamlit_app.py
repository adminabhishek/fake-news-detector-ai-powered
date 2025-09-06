import streamlit as st
import re
import logging
from retrieve import search_web, fetch_all_articles_async
from nli import analyze_evidence
from rank import rank_evidence, categorize_evidence
from verdict import determine_web_search_verdict, determine_ai_verdict, generate_rationale
from reasoning import should_use_ai_reasoning, generate_ai_reasoning

# Configure the page
st.set_page_config(
    page_title="Fake News Detector with Evidence",
    page_icon="search",
    layout="wide"
)

if st.button("Verify Claim", type="primary"):
    if claim.strip():
        with st.spinner("Analyzing claim and gathering evidence..."):
            import time
            start_time = time.time()
            try:
                # 1. Search for the claim
                urls = search_web(claim.strip())
                if not urls:
                    st.warning("No relevant sources found for this claim.")
                    ai_reasoning = generate_ai_reasoning(claim.strip(), [], "UNCLEAR", "No relevant sources found for this claim.")
                    result = {
                        'prediction': "UNCLEAR",
                        'rationale': f"No relevant sources found for this claim.\n\nAI Analysis: {ai_reasoning}" if ai_reasoning else "No relevant sources found for this claim.",
                        'evidence': [],
                        'processing_time': time.time() - start_time,
                        'articles_processed': 0,
                        'ai_reasoning': ai_reasoning
                    }
                else:
                    # 2. Fetch and parse articles
                    articles = fetch_all_articles_async(urls)
                    # 3. Rank evidence
                    all_evidence = rank_evidence(claim.strip(), articles, analyze_evidence)
                    # 4. Categorize evidence
                    supporting, contradicting, neutral = categorize_evidence(all_evidence)
                    # 5. Verdicts
                    web_search_verdict, web_search_reason = determine_web_search_verdict(supporting, contradicting, neutral, claim.strip())
                    ai_verdict, ai_verdict_reason = determine_ai_verdict(claim.strip(), articles)
                    rationale = generate_rationale((web_search_verdict, web_search_reason), supporting, contradicting)
                    ai_reasoning = generate_ai_reasoning(claim.strip(), articles, web_search_verdict, web_search_reason)
                    result = {
                        'web_search_verdict': web_search_verdict,
                        'web_search_reason': web_search_reason,
                        'ai_verdict': ai_verdict,
                        'ai_verdict_reason': ai_verdict_reason,
                        'rationale': rationale,
                        'ai_reasoning': ai_reasoning,
                        'evidence': all_evidence,
                        'processing_time': time.time() - start_time,
                        'articles_processed': len(articles)
                    }
                # Display verdicts
                st.markdown("### 📋 Verdicts")
                # Web Search Verdict
                if result.get('web_search_verdict'):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("#### 🌐 Web Search Verdict")
                        verdict_class = "verdict-unclear"
                        prediction = result['web_search_verdict']
                        if prediction == "TRUE":
                            verdict_class = "verdict-true"
                        elif prediction == "FALSE":
                            verdict_class = "verdict-false"
                        elif prediction == "MIXED":
                            verdict_class = "verdict-mixed"
                        elif prediction == "LIKELY TRUE":
                            verdict_class = "verdict-likely-true"
                        elif prediction == "LIKELY FALSE":
                            verdict_class = "verdict-likely-false"
                        st.markdown(f'<p class="{verdict_class}">{prediction}</p>', unsafe_allow_html=True)
                        if result.get('web_search_reason'):
                            st.info(result['web_search_reason'])
                    with col2:
                        st.markdown("#### 🤖 AI Verdict")
                        if result.get('ai_verdict'):
                            verdict_class = "verdict-unclear"
                            prediction = result['ai_verdict']
                            if prediction == "TRUE":
                                verdict_class = "verdict-true"
                            elif prediction == "FALSE":
                                verdict_class = "verdict-false"
                            elif prediction == "MIXED":
                                verdict_class = "verdict-mixed"
                            elif prediction == "LIKELY TRUE":
                                verdict_class = "verdict-likely-true"
                            elif prediction == "LIKELY FALSE":
                                verdict_class = "verdict-likely-false"
                            st.markdown(f'<p class="{verdict_class}">{prediction}</p>', unsafe_allow_html=True)
                            if result.get('ai_verdict_reason'):
                                st.info(result['ai_verdict_reason'])
                        else:
                            st.warning("AI verdict not available")
                else:
                    # Fallback to original display if separate verdicts not available
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        verdict_class = "verdict-unclear"
                        prediction = result['prediction']
                        if prediction == "TRUE":
                            verdict_class = "verdict-true"
                        elif prediction == "FALSE":
                            verdict_class = "verdict-false"
                        elif prediction == "MIXED":
                            verdict_class = "verdict-mixed"
                        elif prediction == "LIKELY TRUE":
                            verdict_class = "verdict-likely-true"
                        elif prediction == "LIKELY FALSE":
                            verdict_class = "verdict-likely-false"
                        st.markdown(f'<p class="{verdict_class}">{prediction}</p>', unsafe_allow_html=True)
                        st.info(result['rationale'])
                # Display AI Reasoning separately if available
                if result.get('ai_reasoning'):
                    st.markdown("### 🤖 AI Analysis")
                    with st.container():
                        st.markdown(f'<div class="ai-reasoning">{result["ai_reasoning"]}</div>', unsafe_allow_html=True)
                # Display evidence
                st.markdown("### 🔍 Evidence & Sources")
                if result['evidence']:
                    for i, evidence in enumerate(result['evidence']):
                        expander_title = f"Evidence #{i+1}"
                        with st.expander(expander_title):
                            if evidence['sentence']:
                                st.markdown(f'**Sentence:**')
                                st.markdown(f'<div class="evidence-sentence">{evidence["sentence"]}</div>', unsafe_allow_html=True)
                            else:
                                st.warning("No sentence text available")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Entailment", f"{evidence['entailment']:.3f}")
                            with col2:
                                st.metric("Contradiction", f"{evidence['contradiction']:.3f}")
                            with col3:
                                st.metric("Neutral", f"{evidence['neutral']:.3f}")
                            if evidence['entailment'] > 0.7:
                                st.success("**✅ This evidence supports the claim**")
                            elif evidence['contradiction'] > 0.7:
                                st.error("**❌ This evidence contradicts the claim**")
                            else:
                                st.warning("**⚪ This evidence is neutral**")
                            source = evidence['source']
                            st.markdown("---")
                            st.markdown("**Source Information:**")
                            if source.get('title'):
                                st.markdown(f"**Title:** {source['title']}")
                            if source.get('url'):
                                st.markdown(f"**URL:** [{source['url']}]({source['url']})")
                            if source.get('publish_date'):
                                st.markdown(f"**Published:** {source['publish_date']}")
                else:
                    st.warning("No evidence was found for this claim.")
                st.markdown("---")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Processing Time", f"{result['processing_time']:.2f} seconds")
                with col2:
                    st.metric("Articles Processed", result['articles_processed'])
                with col3:
                    st.metric("Evidence Items", len(result['evidence']))
            except Exception as e:
                st.error(f"An unexpected error occurred: {str(e)}")
    else:
        st.warning("Please enter a claim to verify.")
                                if evidence['entailment'] > 0.7:
                                    st.success("**✅ This evidence supports the claim**")
                                elif evidence['contradiction'] > 0.7:
                                    st.error("**❌ This evidence contradicts the claim**")
                                else:
                                    st.warning("**⚪ This evidence is neutral**")
                                
                                # Display source information
                                source = evidence['source']
                                st.markdown("---")
                                st.markdown("**Source Information:**")
                                
                                if source.get('title'):
                                    st.markdown(f"**Title:** {source['title']}")
                                if source.get('url'):
                                    st.markdown(f"**URL:** [{source['url']}]({source['url']})")
                                if source.get('publish_date'):
                                    st.markdown(f"**Published:** {source['publish_date']}")
                    else:
                        st.warning("No evidence was found for this claim.")
                    
                    # Display metrics
                    st.markdown("---")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Processing Time", f"{result['processing_time']:.2f} seconds")
                    with col2:
                        st.metric("Articles Processed", result['articles_processed'])
                    with col3:
                        st.metric("Evidence Items", len(result['evidence']))
                
                else:
                    st.error(f"Error: {response.status_code} - {response.text}")
                    
            except requests.exceptions.RequestException as e:
                st.error(f"Failed to connect to the verification service. Please make sure the API server is running.")
                st.code("Start the server with: uvicorn api:app --reload --host 127.0.0.1 --port 8000")
            except Exception as e:
                st.error(f"An unexpected error occurred: {str(e)}")
    else:
        st.warning("Please enter a claim to verify.")

with st.sidebar:
    st.markdown("### ℹ️ How It Works")
    st.markdown("""
    1. **Enter** a claim or headline
    2. **Click** the Verify button
    3. **View** the verdict and evidence
    
    The system:
    - Searches reliable news sources
    - Analyzes content using AI
    - Provides evidence-based verdicts
    """)
    st.markdown("### ⚙️ API Status")
    st.info("This app runs fully on Streamlit Cloud. No external API server required.")

# Footer
st.markdown("---")
st.markdown("*This tool uses AI to analyze news content. Verify critical information with multiple sources.*")