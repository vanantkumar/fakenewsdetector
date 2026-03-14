import streamlit as st
import re

# App config
st.set_page_config(page_title="Fake News Detector", page_icon="📰", layout="wide")

# FAKE NEWS DETECTION RULES (keyword-based, no ML)
FAKE_PATTERNS = [
    # Sensational words
    r'\b(breaking|shocking|urgent|exposed|finally|admit|confess)\b',
    r'\b(free|everyone|all|now|claim|secret|hidden|conspiracy)\b',
    r'\b(fake|hoax|scam|lie|proof|caught|microchip)\b',
    
    # Clickbait
    r'[!]{2,}',  # Multiple exclamations
    r'\b(cure|miracle|instant|guaranteed|100%)\b',
    
    # Numbers that look scammy
    r'\$?[\d,]+\s*(billion|million|dollar)s?\b',
]

REAL_PATTERNS = [
    r'\b(study|report|data|analysis|research|confirmed)\b',
    r'\b(federal|university|government|organization)\b',
]

def detect_fake_news(title, content):
    """Pure regex + keyword detection"""
    text = f"{title} {content}".lower()
    
    # Count fake indicators
    fake_score = 0
    for pattern in FAKE_PATTERNS:
        fake_score += len(re.findall(pattern, text, re.IGNORECASE))
    
    # Count real indicators  
    real_score = 0
    for pattern in REAL_PATTERNS:
        real_score += len(re.findall(pattern, text, re.IGNORECASE))
    
    # Bonus points for ALL CAPS and exclamations
    fake_score += text.count('!') * 3
    fake_score += sum(1 for c in text if c.isupper() and c != 'I')
    
    # Calculate probabilities
    total_signals = fake_score + real_score + 1
    fake_prob = min(98, (fake_score / total_signals) * 100)
    real_prob = min(98, (real_score / total_signals) * 100)
    
    is_fake = fake_prob > real_prob
    confidence = max(fake_prob, real_prob) / 100
    
    return {
        'is_fake': is_fake,
        'fake_prob': fake_prob,
        'real_prob': real_prob,
        'confidence': confidence,
        'fake_signals': int(fake_score),
        'real_signals': int(real_score),
        'exclamation_count': text.count('!')
    }

# === STREAMLIT APP ===
st.title("📰 Fake News Detector")
st.markdown("**Instant detection • Zero dependencies • Works everywhere!**")

# Sidebar explanation
with st.sidebar:
    st.header("🎯 How it works")
    st.markdown("""
    **Detects:**
    - **BREAKING/SHOCKING** headlines
    - **FREE** clickbait  
    - **!!!** exclamations
    - Conspiracy words
    - ALL CAPS screaming
    
    **Real news has:**
    - study/report/data
    - federal/university
    """)

# Input form
st.header("🔍 Paste News Here")
col1, col2 = st.columns([1, 3])

with col1:
    title = st.text_input("**Headline**", 
                         placeholder="NASA admits Earth is FLAT!!!")
with col2:
    article = st.text_area("**Article**", 
                          placeholder="Conspiracy finally exposed...", 
                          height=100)

# ANALYZE BUTTON
if st.button("🚀 CHECK FOR FAKE NEWS", type="primary", use_container_width=True):
    if title or article:
        result = detect_fake_news(title, article)
        
        # BIG RESULTS
        st.header("📊 RESULTS")
        col1, col2, col3 = st.columns(3)
        
        verdict = "🛑 **FAKE NEWS**" if result['is_fake'] else "✅ **LEGITIMATE**"
        with col1:
            st.metric("Verdict", verdict, delta="High confidence")
        with col2:
            st.metric("Confidence", f"{result['confidence']:.0%}")
        with col3:
            st.metric("Fake Score", f"{result['fake_prob']:.0%}")
        
        # Details
        col1, col2 = st.columns(2)
        with col1:
            st.metric("🚨 Fake Signals", result['fake_signals'])
            st.metric("❗ Exclamations", result['exclamation_count'])
        with col2:
            st.metric("✅ Real Signals", result['real_signals'])
        
        # Explanation
        st.subheader("🔍 What triggered this?")
        if result['is_fake']:
            st.error("""
            **🚨 RED FLAGS DETECTED:**
            - Sensational keywords (BREAKING, FREE, SHOCKING)
            - Too many exclamation marks (!!!)
            - Conspiracy language patterns
            - ALL CAPS screaming
            """)
        else:
            st.success("""
            **✅ CLEAN NEWS:**
            - Professional language
            - Credible source words
            - No clickbait patterns
            """)
    else:
        st.warning("👆 Enter headline or article first!")

# QUICK TESTS
st.header("⚡ Quick Tests")
col1, col2, col3 = st.columns(3)

if col1.button("🛑 Test FAKE", use_container_width=True):
    st.session_state.test = "NASA admits Earth FLAT!!! Free iPhones for all!!!"
    
if col2.button("✅ Test REAL", use_container_width=True):
    st.session_state.test = "Federal Reserve cuts rates. Economic report released."

if col3.button("🎲 Random", use_container_width=True):
    import random
    tests = ["SHOCKING: Cure found!", "University study published", "BREAKING: Free money!"]
    st.session_state.test = random.choice(tests)

if 'test' in st.session_state:
    st.info(f"**Test:** {st.session_state.test}")

# Footer
st.markdown("---")
st.markdown("""
<center><small>
🎉 Pure Python • No Dependencies • Instant Results<br>
Made with ❤️ for Streamlit
</small></center>
""")
