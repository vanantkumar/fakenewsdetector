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
st.set_page_config(page_title="Fake News Detector", layout="wide")

# -------------------- CSS FIX --------------------
st.markdown("""
<style>

/* REMOVE TOP WHITE SPACE COMPLETELY */
header, footer {
    visibility: hidden;
}

.block-container {
    padding-top: 0rem;
    padding-bottom: 0rem;
}

/* BACKGROUND IMAGE */
.stApp {
    background-image: url("https://media.gettyimages.com/id/1335171779/photo/fake-or-real.jpg?s=612x612&w=0&k=20&c=4ihkaDS1Ry0i9ev41--smxxH5ir8vWM4Q4JL93VhC_k=");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}

/* DARK OVERLAY */
.stApp::before {
    content: "";
    position: fixed;
    top:0; left:0;
    width:100%; height:100%;
    background: rgba(0,0,0,0.65);
    z-index:0;
}

/* LEFT PANEL */
.left {
    position: relative;
    z-index: 1;
    color: white;
    padding: 120px 60px;
}

.left h1 {
    font-size: 48px;
    font-weight: bold;
}

.left p {
    margin-top: 20px;
    color: #ddd;
}

/* RIGHT CARD */
.card {
    position: relative;
    z-index: 1;
    background: rgba(255,255,255,0.95);
    padding: 30px;
    border-radius: 12px;
    max-width: 420px;
    margin: auto;
    margin-top: 120px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}

/* BUTTON */
.stButton>button {
    width: 100%;
    border-radius: 6px;
    background: #2575fc;
    color: white;
    font-weight: bold;
}

</style>
""", unsafe_allow_html=True)

# -------------------- DATABASE --------------------
conn = sqlite3.connect("app.db", check_same_thread=False)
c = conn.cursor()

c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT, role TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS history (username TEXT, news TEXT, result TEXT)")

if not c.execute("SELECT * FROM users WHERE username='admin'").fetchone():
    c.execute("INSERT INTO users VALUES (?, ?, ?)",
              ("admin", hashlib.sha256("admin123".encode()).hexdigest(), "admin"))
    conn.commit()

# -------------------- SESSION --------------------
if "user" not in st.session_state:
    st.session_state["user"] = None

if "page" not in st.session_state:
    st.session_state["page"] = "Analyze"

if "auth_mode" not in st.session_state:
    st.session_state["auth_mode"] = "login"

# -------------------- LOGIN --------------------
if not st.session_state["user"]:

    col1, col2 = st.columns([1,1])

    # LEFT SIDE
    with col1:
        st.markdown("""
        <div class="left">
            <h1>📰 Fake News Detector</h1>
            <p>Detect fake news using AI and real-time verification.</p>
        </div>
        """, unsafe_allow_html=True)

    # RIGHT SIDE
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)

        if st.session_state["auth_mode"] == "login":

            st.markdown("### Login")

            username = st.text_input("Username")
            password = st.text_input("Password", type="password")

            if st.button("Login"):
                user = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()

                if user and hashlib.sha256(password.encode()).hexdigest() == user[1]:
                    st.session_state["user"] = username
                    st.rerun()
                else:
                    st.error("Invalid credentials")

            # 👇 Signup BELOW login
            if st.button("Signup"):
                st.session_state["auth_mode"] = "signup"
                st.rerun()

        else:
            st.markdown("### Signup")

            new_user = st.text_input("New Username")
            new_pass = st.text_input("New Password", type="password")

            if st.button("Create Account"):
                if new_user and new_pass:
                    c.execute("INSERT INTO users VALUES (?, ?, ?)",
                              (new_user, hashlib.sha256(new_pass.encode()).hexdigest(), "user"))
                    conn.commit()
                    st.success("Account created")

            if st.button("Back to Login"):
                st.session_state["auth_mode"] = "login"
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    st.stop()

# -------------------- GEMINI --------------------
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel(
    next(m.name for m in genai.list_models() if "generateContent" in m.supported_generation_methods)
)

# -------------------- FETCH NEWS --------------------
def fetch_real_news(query):
    try:
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"
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

# -------------------- MAIN APP --------------------
st.markdown("<h1 style='text-align:center;color:white;'>📰 Fake News Detector</h1>", unsafe_allow_html=True)

news = st.text_area("Enter News")

if st.button("Analyze"):
    with st.spinner("Analyzing..."):
        time.sleep(1)
        result = analyze_news(news)

    st.write(result)

# -------------------- LOGOUT --------------------
if st.button("Logout"):
    st.session_state["user"] = None
    st.rerun()
