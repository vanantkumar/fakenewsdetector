import streamlit as st
import requests
try:
    from bs4 import BeautifulSoup
except:
    import os
    os.system("pip install beautifulsoup4")
    from bs4 import BeautifulSoup
import sqlite3
from passlib.hash import pbkdf2_sha256
import google.generativeai as genai
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime
import urllib.parse
from xml.etree import ElementTree as ET
import pandas as pd
import re

# -------------------- PAGE CONFIG --------------------
st.set_page_config(page_title="AI Fake News Detector", layout="wide")

# -------------------- PREMIUM UI --------------------
st.markdown("""
<style>
body {background-color:#0E1117;color:white;}
.block-container {padding:2rem;}
.card {
    background:#1E1E1E;
    padding:20px;
    border-radius:15px;
    box-shadow:0 4px 10px rgba(0,0,0,0.5);
}
.metric {
    background:#262730;
    padding:15px;
    border-radius:10px;
    text-align:center;
}
</style>
""", unsafe_allow_html=True)

# -------------------- DATABASE --------------------
conn = sqlite3.connect("app.db", check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT, role TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS history (username TEXT, news TEXT, result TEXT)")

    if not c.execute("SELECT * FROM users WHERE username='admin'").fetchone():
        c.execute("INSERT INTO users VALUES (?, ?, ?)",
                  ("admin", pbkdf2_sha256.hash("admin123"), "admin"))
        conn.commit()

init_db()

# -------------------- SESSION --------------------
if "user" not in st.session_state:
    st.session_state["user"] = None

# -------------------- AUTH --------------------
def login_ui():
    st.title("🔐 Login / Signup")
    st.info("Admin → admin / admin123")

    option = st.radio("Choose", ["Login", "Signup"])
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if option == "Signup":
        if st.button("Create Account"):
            c.execute("INSERT INTO users VALUES (?, ?, ?)",
                      (u, pbkdf2_sha256.hash(p), "user"))
            conn.commit()
            st.success("Account created")
    else:
        if st.button("Login"):
            user = c.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
            if user and pbkdf2_sha256.verify(p, user[1]):
                st.session_state["user"] = u
                st.rerun()
            else:
                st.error("Invalid credentials")

if not st.session_state["user"]:
    login_ui()
    st.stop()

# -------------------- GEMINI --------------------
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel(
    next(m.name for m in genai.list_models() if "generateContent" in m.supported_generation_methods)
)

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
    Confidence: %
    Explanation:
    """
    return model.generate_content(prompt).text

# -------------------- SIDEBAR --------------------
st.sidebar.title("🧭 Navigation")
page = st.sidebar.radio("Go to", ["Analyze", "Dashboard", "History"])
st.sidebar.write(f"👤 {st.session_state['user']}")

# -------------------- ANALYZE PAGE --------------------
if page == "Analyze":
    st.title("🧠 Fake News Detector")

    col1, col2 = st.columns([2,1])

    with col1:
        text = st.text_area("📰 Enter News", height=200)

    if st.button("Analyze"):
        result = analyze_news(text)

        confidence = int(re.search(r'(\d+)%', result).group(1)) if re.search(r'(\d+)%', result) else 50

        # RESULT UI
        if "fake" in result.lower():
            st.error("🚨 FAKE NEWS")
        elif "real" in result.lower():
            st.success("✅ REAL NEWS")
        else:
            st.info("🤔 UNVERIFIED")

        # CONFIDENCE
        st.metric("Confidence", f"{confidence}%")
        st.progress(confidence)

        st.markdown(f"<div class='card'>{result}</div>", unsafe_allow_html=True)

        c.execute("INSERT INTO history VALUES (?, ?, ?)",
                  (st.session_state["user"], text, result))
        conn.commit()

# -------------------- DASHBOARD --------------------
elif page == "Dashboard":
    st.title("📊 Analytics Dashboard")

    rows = c.execute("SELECT * FROM history").fetchall()

    if rows:
        df = pd.DataFrame(rows, columns=["User","News","Result"])

        fake = df["Result"].str.contains("fake", case=False).sum()
        real = df["Result"].str.contains("real", case=False).sum()
        unv = df["Result"].str.contains("unverified", case=False).sum()

        c1, c2, c3 = st.columns(3)

        c1.metric("Fake News", fake)
        c2.metric("Real News", real)
        c3.metric("Unverified", unv)

        st.bar_chart({"Fake":[fake], "Real":[real], "Unverified":[unv]})
    else:
        st.info("No data yet")

# -------------------- HISTORY --------------------
elif page == "History":
    st.title("📜 History")

    rows = c.execute("SELECT * FROM history WHERE username=?",
                     (st.session_state["user"],)).fetchall()

    for r in rows[::-1]:
        st.markdown(f"<div class='card'>📰 {r[1][:150]}...<br><br>{r[2]}</div>", unsafe_allow_html=True)

# -------------------- LOGOUT --------------------
if st.sidebar.button("Logout"):
    st.session_state["user"] = None
    st.rerun()
