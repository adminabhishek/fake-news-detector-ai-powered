import streamlit as st
import requests
import json
import re

# Configure the page
st.set_page_config(
    page_title="Fake News Detector with Evidence",
    page_icon="search",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {font-size: 3rem; color: #1f77b4; text-align: center;}
    .verdict-true {color: green; font-weight: bold; font-size: 1.5rem;}
    .verdict-false {color: red; font-weight: bold; font-size: 1.5rem;}
    .verdict-mixed {color: orange; font-weight: bold; font-size: 1.5rem;}
    .verdict-unclear {color: gray; font-weight: bold; font-size: 1.5rem;}
    .verdict-likely-true {color: #2E8B57; font-weight: bold; font-size: 1.5rem;}
    .verdict-likely-false {color: #DC143C; font-weight: bold; font-size: 1.5rem;}
    .evidence-card {border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px;}
    .source-link {color: #0066cc; text-decoration: none;}
    .ai-reasoning {background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 4px solid #6f42c1;}
    .evidence-sentence {font-size: 0.95em; line-height: 1.4; white-space: pre-wrap;}
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">Fake News Detector — with Evidence & Sources</h1>', unsafe_allow_html=True)
st.markdown("---")

# Input section
claim = st.text_area(
    "Paste headline or short article:",
    height=100,
    placeholder="Enter the claim you want to verify..."
)

def clean_text(text, max_length=80):
    """Clean and truncate text for display"""
    if not text:
        return "No text available"
    
    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Truncate if too long
    if len(text) > max_length:
        return text[:max_length] + '...'
    return text

if st.button("Verify Claim", type="primary"):
    if claim.strip():
        with st.spinner("Analyzing claim and gathering evidence..."):
            try:
                # Call the FastAPI backend
                response = requests.post(
                    "http://127.0.0.1:8000/check",
                    json={"claim": claim.strip()},
                    timeout=120
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
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

                        # AI Verdict
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
                            # Create a simple expander title
                            expander_title = f"Evidence #{i+1}"
                            
                            with st.expander(expander_title):
                                # Display the sentence with proper formatting
                                if evidence['sentence']:
                                    st.markdown(f'**Sentence:**')
                                    st.markdown(f'<div class="evidence-sentence">{evidence["sentence"]}</div>', unsafe_allow_html=True)
                                else:
                                    st.warning("No sentence text available")
                                
                                # Display scores
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Entailment", f"{evidence['entailment']:.3f}")
                                with col2:
                                    st.metric("Contradiction", f"{evidence['contradiction']:.3f}")
                                with col3:
                                    st.metric("Neutral", f"{evidence['neutral']:.3f}")
                                
                                # Color code based on evidence type
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

# Sidebar with instructions
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
    try:
        status_response = requests.get("http://127.0.0.1:8000/", timeout=5)
        if status_response.status_code == 200:
            st.success("✅ API Server is online")
        else:
            st.error("❌ API Server error")
    except:
        st.error("❌ API Server is offline")

# Footer
st.markdown("---")
st.markdown("*This tool uses AI to analyze news content. Verify critical information with multiple sources.*")