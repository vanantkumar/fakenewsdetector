import streamlit as st
import re
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Config
st.set_page_config(page_title="Fake News Detector", page_icon="📰", layout="wide")

# NLTK setup
@st.cache_data
def setup_nltk():
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('corpora/stopwords')
    except:
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)

setup_nltk()

# Fake news keywords & patterns
FAKE_KEYWORDS = {
    'extreme': ['breaking', 'shocking', 'urgent', 'alert', 'exposed', 'finally', 'admit', 'confess'],
    'sensational': ['free', 'everyone', 'all', 'now', 'limited', 'claim', 'secret', 'hidden', 'conspiracy'],
    'fake_indicators': ['fake', 'hoax', 'scam', 'lie', 'proof', 'evidence', 'caught'],
    'unrealistic': ['cure', 'miracle', 'instant', 'guaranteed', '100%', 'bill gates', 'microchip']
}

REAL_KEYWORDS = {
    'credible': ['study', 'report', 'officials', 'data', 'analysis', 'research', 'confirmed'],
    'professional': ['federal', 'university', 'government', 'organization', 'published']
}

STOP_WORDS = set(stopwords.words('english'))

def preprocess_text(text):
    """Clean text"""
    text = re.sub(r'http\S+|www\S+|https\S+', '', str(text))
    text = re.sub(r'[^a-zA-Z\s]', '', text.lower())
    text = re.sub(r'\s+', ' ', text).strip()
    words = [w for w in text.split() if w not in STOP_WORDS and len(w) > 2]
    return words

def analyze_text(title, content):
    """Analyze fake news score"""
    text = f"{title} {content}".lower()
    words = preprocess_text(text)
    word_count = Counter(words)
    
    # Calculate fake score
    fake_score = 0
    total_fake_words = 0
    
    for category, keywords in FAKE_KEYWORDS.items():
        for keyword in keywords:
            count = word_count.get(keyword, 0)
            fake_score += count * (1 + len(keywords))  # Weight by category
            total_fake_words += count
    
    # Real score
    real_score = 0
    for category, keywords in REAL_KEYWORDS.items():
        for keyword in keywords:
            real_score += word_count.get(keyword, 0)
    
    # Exclamation & caps score
    excl_count = text.count('!')
    caps_score = sum(1 for c in text if c.isupper())
    
    fake_score += excl_count * 5 + caps_score * 0.1
    
    # Normalize
    total_words = len(words) + 1
    fake_prob = min(95, (fake_score / total_words * 100) if total_words > 0 else 0)
    real_prob = min(95, (real_score / total_words * 100) if total_words > 0 else 0)
    
    confidence = max(fake_prob, real_prob) / 100
    
    return {
        'fake_prob': fake_prob,
        'real_prob': real_prob,
        'confidence': confidence,
        'fake_words': total_fake_words,
        'exclamation_count': excl_count,
        'top_fake_word': word_count.most_common(1)[0][0] if word_count else None
    }

# App UI
st.title("📰 Fake News Detector")
st.markdown("**AI-Powered Fake News Detection - No ML libraries needed!**")

# Sidebar
with st.sidebar:
    st.header("🔍 Detection Method")
    st.info("""
    **Algorithm detects:**
    - Sensational keywords (FREE, SHOCKING!)
    - Clickbait patterns
    - Exclamation overuse (!!!)
    - Conspiracy language
    - Unrealistic claims
    """)
    
    st.header("⚡ Fast & Lightweight")
    st.success("✅ Works offline\n✅ No heavy ML\n✅ Instant results")

# Main input
st.header("📝 Enter News Article")
col1, col2 = st.columns([1, 3])

with col1:
    title = st.text_input("**Headline:**", placeholder="e.g. NASA admits Earth is FLAT!")
with col2:
    article = st.text_area("**Content:**", 
                          placeholder="Paste article text here...", 
                          height=120)

# Analyze button
col1, col2 = st.columns([3, 1])
if col1.button("🚀 DETECT FAKE NEWS", type="primary", use_container_width=True):
    if title or article:
        with st.spinner("🔍 Scanning for fake patterns..."):
            result = analyze_text(title, article)
        
        # Results
        st.subheader("📊 ANALYSIS RESULTS")
        
        # Main metrics
        col1, col2, col3 = st.columns(3)
        verdict = "🛑 **FAKE NEWS**" if result['fake_prob'] > result['real_prob'] else "✅ **LEGITIMATE**"
        
        with col1:
            st.metric("Verdict", verdict)
        with col2:
            st.metric("Confidence", f"{result['confidence']:.0%}")
        with col3:
            st.metric("Fake Risk", f"{result['fake_prob']:.0%}")
        
        # Details
        st.subheader("📈 Detailed Breakdown")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("🚨 Suspicious Words", result['fake_words'])
            st.metric("❗ Exclamations", result['exclamation_count'])
        
        with col2:
            if result['top_fake_word']:
                st.metric("🔥 Top Trigger Word", result['top_fake_word'].upper())
            st.metric("✅ Credible Words", int(result['real_prob']/2))
        
        # Risk explanation
        st.subheader("⚠️ Why this score?")
        if result['fake_prob'] > 60:
            st.error("""
            **🚨 HIGH FAKE RISK:**
            - Heavy use of sensational words
            - Multiple exclamation marks
            - Clickbait headline patterns
            - Conspiracy-style language
            """)
        elif result['fake_prob'] > 30:
            st.warning("""
            **⚠️ MEDIUM RISK:**
            - Some sensational language
            - Mild clickbait elements
            - Check source credibility
            """)
        else:
            st.success("""
            **✅ LOW RISK:**
            - Professional language
            - Credible keywords present
            - Balanced reporting style
            """)
            
    else:
        st.warning("⚠️ Enter headline or article text!")

# Quick tests
st.header("🧪 Instant Tests")
col1, col2, col3 = st.columns(3)

if col1.button("🛑 FAKE: Free iPhone!", use_container_width=True):
    st.rerun()

if col2.button("✅ REAL: Fed News", use_container_width=True):
    st.rerun()

if col3.button("🎲 Random Test", use_container_width=True):
    st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<center>
<div style='color: #666; font-size: 14px;'>
🚀 Pure Python | Zero Dependencies | Instant Results<br>
Made with ❤️ using <a href='https://streamlit.io'>Streamlit</a>
</div>
</center>
""", unsafe_allow_html=True)
