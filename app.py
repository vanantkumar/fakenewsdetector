import streamlit as st
import requests
import sqlite3
import hashlib
import google.generativeai as genai
from datetime import datetime
import urllib.parse
from xml.etree import ElementTree as ET
import pandas as pd
import re
import time

# -------------------- CONFIG --------------------
st.set_page_config(page_title="AI Fake News Detector", layout="wide")

# -------------------- PREMIUM CSS --------------------
st.markdown("""
<style>
body {
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    color: white;
}
.block-container {padding:2rem;}

.card {
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(10px);
    border-radius: 15px;
    padding: 20px;
    margin-top: 15px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
}

.stButton>button {
    border-radius: 12px;
    background: linear-gradient(90deg, #ff512f, #dd2476);
    color: white;
    height: 3em;
    width: 100%;
}
</style>
""", unsafe_allow_html=True)

# -------------------- DATABASE --------------------
conn = sqlite3.connect("app.db", check_same_thread=False)
c = conn.cursor()

c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT, role TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS history (username TEXT, news TEXT, result TEXT)")

# Default admin
if not c.execute("SELECT * FROM users WHERE username='admin'").fetchone():
    c.execute("INSERT INTO users VALUES (?, ?, ?)",
              ("admin", hashlib.sha256("admin123".encode()).hexdigest(), "admin"))
    conn.commit()

# -------------------- SESSION --------------------
if "user" not in st.session_state:
    st.session_state["user"] = None

# -------------------- LOGIN POPUP --------------------
if not st.session_state["user"]:
    st.markdown("<h1 style='text-align:center;'>🧠 AI Fake News Detector</h1>", unsafe_allow_html=True)

    if "show_login" not in st.session_state:
        st.session_state.show_login = False
    if "show_signup" not in st.session_state:
        st.session_state.show_signup = False

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔐 Login"):
            st.session_state.show_login = True

    with col2:
        if st.button("🆕 Signup"):
            st.session_state.show_signup = True

    # LOGIN
    if st.session_state.show_login:
        st.markdown("### 🔐 Login")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")

        if st.button("Submit Login"):
            user = c.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
            if user and hashlib.sha256(p.encode()).hexdigest() == user[1]:
                st.session_state["user"] = u
                st.session_state.show_login = False
                st.rerun()
            else:
                st.error("Invalid credentials")

    # SIGNUP
    if st.session_state.show_signup:
        st.markdown("### 🆕 Signup")
        u = st.text_input("New Username")
        p = st.text_input("New Password", type="password")

        if st.button("Create Account"):
            c.execute("INSERT INTO users VALUES (?, ?, ?)",
                      (u, hashlib.sha256(p.encode()).hexdigest(), "user"))
            conn.commit()
            st.success("Account created")
            st.session_state.show_signup = False

    st.stop()

# -------------------- GEMINI --------------------
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model_name = next(
    m.name for m in genai.list_models()
    if "generateContent" in m.supported_generation_methods
)
model = genai.GenerativeModel(model_name)

# -------------------- NEWS FETCH --------------------
def fetch_real_news(q):
    try:
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=en-IN&gl=IN&ceid=IN:en"
        root = ET.fromstring(requests.get(url).content)
        return [i.find("title").text for i in root.findall(".//item")[:5]]
    except:
        return []

# -------------------- ANALYSIS --------------------
def analyze_news(text):
    headlines = "\n".join(fetch_real_news(text)) or "No news found"

    prompt = f"""
    Date: {datetime.now().strftime("%B %Y")}

    News: {text}

    Real Headlines:
    {headlines}

    Verdict: Real/Fake/Unverified
    Confidence: XX%
    Explanation:
    """

    return model.generate_content(prompt).text

# -------------------- SIDEBAR --------------------
st.sidebar.title("🧭 Navigation")
page = st.sidebar.radio("Go to", ["Analyze", "Dashboard", "History"])
st.sidebar.write(f"👤 {st.session_state['user']}")

# -------------------- ANALYZE --------------------
if page == "Analyze":
    st.markdown("<h2>🧠 Analyze News</h2>", unsafe_allow_html=True)

    news = st.text_area("Enter News", height=200)

    if st.button("Analyze"):
        with st.spinner("🤖 AI analyzing..."):
            progress = st.progress(0)
            for i in range(100):
                time.sleep(0.01)
                progress.progress(i + 1)

            result = analyze_news(news)

        confidence = int(re.search(r'(\d+)%', result).group(1)) if re.search(r'(\d+)%', result) else 50

        if "fake" in result.lower():
            st.error("🚨 FAKE NEWS")
        elif "real" in result.lower():
            st.success("✅ REAL NEWS")
        else:
            st.info("🤔 UNVERIFIED")

        st.metric("Confidence", f"{confidence}%")
        st.progress(confidence)

        st.markdown(f"<div class='card'>{result}</div>", unsafe_allow_html=True)

        c.execute("INSERT INTO history VALUES (?, ?, ?)",
                  (st.session_state["user"], news, result))
        conn.commit()

# -------------------- DASHBOARD --------------------
elif page == "Dashboard":
    st.markdown("<h2>📊 Dashboard</h2>", unsafe_allow_html=True)

    rows = c.execute("SELECT * FROM history").fetchall()

    if rows:
        df = pd.DataFrame(rows, columns=["User","News","Result"])

        fake = df["Result"].str.contains("fake", case=False).sum()
        real = df["Result"].str.contains("real", case=False).sum()
        unv = df["Result"].str.contains("unverified", case=False).sum()

        col1, col2, col3 = st.columns(3)

        col1.markdown(f"<div class='card'>🚨 Fake<br><h2>{fake}</h2></div>", unsafe_allow_html=True)
        col2.markdown(f"<div class='card'>✅ Real<br><h2>{real}</h2></div>", unsafe_allow_html=True)
        col3.markdown(f"<div class='card'>🤔 Unverified<br><h2>{unv}</h2></div>", unsafe_allow_html=True)

        st.bar_chart({"Fake":[fake], "Real":[real], "Unverified":[unv]})

# -------------------- HISTORY --------------------
elif page == "History":
    st.markdown("<h2>📜 History</h2>", unsafe_allow_html=True)

    rows = c.execute("SELECT * FROM history WHERE username=?",
                     (st.session_state["user"],)).fetchall()

    for r in rows[::-1]:
        st.markdown(f"<div class='card'>📰 {r[1][:150]}...<br><br>{r[2]}</div>", unsafe_allow_html=True)

# -------------------- LOGOUT --------------------
if st.sidebar.button("Logout"):
    st.session_state["user"] = None
    st.rerun()
