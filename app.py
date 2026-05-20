import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
import numpy as np
from gotrue import SyncGoTrueClient, SyncMemoryStorage
import httpx

st.set_page_config(page_title="simu · Dashboard", page_icon="🟢", layout="wide", initial_sidebar_state="expanded")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
BASE_URL = "http://localhost:8501"

def get_auth_client():
    return SyncGoTrueClient(url=f"{SUPABASE_URL}/auth/v1", headers={"apikey": SUPABASE_KEY}, storage=SyncMemoryStorage())

def supabase_request(method, path, data=None, token=None, params=None):
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json", "Prefer": "return=representation"}
    if token: headers["Authorization"] = f"Bearer {token}"
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    with httpx.Client() as client:
        if method == "GET": r = client.get(url, headers=headers, params=params)
        elif method == "POST": r = client.post(url, headers=headers, json=data)
        elif method == "PATCH": r = client.patch(url, headers=headers, json=data)
        return r.json() if r.content else []

# ── Session state ──────────────────────────────────────────────────────────────
for k,v in [("user",None),("access_token",None),("auth_page","landing"),("current_campaign",None),("show_launch",False),("campaign_step",1),("campaign_draft",{})]:
    if k not in st.session_state: st.session_state[k] = v

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&family=DM+Serif+Display&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background-color: #0a2a24; color: #e8f5f1; }
header[data-testid="stHeader"] { display: none !important; }
#MainMenu { display: none !important; }
footer { display: none !important; }
section[data-testid="stSidebar"] { background-color: #0d332c !important; border-right: 1px solid rgba(74,222,170,0.12); }
section[data-testid="stSidebar"] * { color: #e8f5f1 !important; }
div[data-testid="metric-container"] { background: #0d332c; border: 1px solid rgba(74,222,170,0.15); border-radius: 10px; padding: 16px 20px; }
div[data-testid="metric-container"] label { color: rgba(232,245,241,0.5) !important; font-size: 12px !important; text-transform: uppercase; }
div[data-testid="metric-container"] div[data-testid="stMetricValue"] { color: #ffffff !important; font-size: 28px !important; font-weight: 500; }
div[data-testid="metric-container"] div[data-testid="stMetricDelta"] { color: #4adeaa !important; }
div[data-testid="stMetricValue"] { color: #ffffff !important; }
div[data-testid="stMetricLabel"] { color: rgba(232,245,241,0.9) !important; font-size: 13px !important; }
h1, h2, h3 { color: #ffffff !important; }
hr { border-color: rgba(74,222,170,0.1); }
input, input[type="text"], input[type="password"], input[type="email"] { color: #e8f5f1 !important; background-color: rgba(255,255,255,0.04) !important; caret-color: #4adeaa !important; }
input:focus { background-color: #0d332c !important; color: #e8f5f1 !important; }
textarea { color: #e8f5f1 !important; background-color: rgba(255,255,255,0.04) !important; border: 1px solid rgba(74,222,170,0.2) !important; border-radius: 8px !important; }
textarea:focus { background-color: #0d332c !important; color: #e8f5f1 !important; }
div[data-testid="stTextInput"] label, div[data-testid="stTextArea"] label { color: rgba(232,245,241,0.6) !important; font-size: 12px !important; }
div[data-baseweb="base-input"], div[data-baseweb="base-input"] > div { background-color: rgba(255,255,255,0.04) !important; }
div[data-baseweb="base-input"] input { color: #e8f5f1 !important; background: transparent !important; }
div[data-baseweb="select"] div { color: #e8f5f1 !important; background-color: rgba(255,255,255,0.04) !important; }
div[data-baseweb="select"] span { color: #e8f5f1 !important; }
div[data-testid="stSelectbox"] label { color: rgba(232,245,241,0.6) !important; }
.stButton button { background: #4adeaa !important; color: #0a2a24 !important; border: none !important; border-radius: 8px !important; font-weight: 600 !important; font-family: 'DM Sans', sans-serif !important; transition: all 0.2s !important; }
.stButton button:hover { background: #6be8bc !important; }
button[data-testid="baseButton-secondary"] { background: rgba(255,255,255,0.08) !important; color: #e8f5f1 !important; }
div[data-testid="stCheckbox"] label p { color: #e8f5f1 !important; font-size: 14px !important; }
div[data-testid="stRadio"] label p { color: #e8f5f1 !important; }
div[data-testid="stRadio"] label { color: #e8f5f1 !important; }
span[data-baseweb="tag"] { background-color: rgba(74,222,170,0.15) !important; border-color: rgba(74,222,170,0.3) !important; }
span[data-baseweb="tag"] span { color: #4adeaa !important; }
.voice-card { background: #0d332c; border-left: 3px solid rgba(74,222,170,0.5); border-radius: 0 8px 8px 0; padding: 14px 16px; margin-bottom: 12px; border-top: 1px solid rgba(74,222,170,0.08); border-right: 1px solid rgba(74,222,170,0.08); border-bottom: 1px solid rgba(74,222,170,0.08); }
.voice-text { font-size: 14px; color: rgba(232,245,241,0.85); line-height: 1.6; margin-bottom: 8px; }
.voice-meta { font-size: 11px; color: rgba(232,245,241,0.35); }
.voice-badge { background: rgba(74,222,170,0.1); color: rgba(74,222,170,0.8); padding: 1px 7px; border-radius: 3px; font-weight: 500; margin: 0 6px; }
.live-dot { display: inline-block; width: 8px; height: 8px; background: #4adeaa; border-radius: 50%; margin-right: 6px; }
.section-label { font-size: 10px; letter-spacing: 1px; text-transform: uppercase; color: rgba(74,222,170,0.5); margin-bottom: 4px; }
.campaign-title { font-size: 22px; font-weight: 500; color: #fff; letter-spacing: -0.3px; margin-bottom: 4px; }
.campaign-meta { font-size: 12px; color: rgba(232,245,241,0.4); }
.step-bar { display: flex; gap: 6px; margin-bottom: 28px; }
.step-pip { height: 4px; flex: 1; border-radius: 2px; background: rgba(74,222,170,0.15); }
.step-pip.active { background: #4adeaa; }
.step-pip.done { background: rgba(74,222,170,0.5); }
.prompt-block { background: rgba(255,255,255,0.03); border-left: 2px solid rgba(74,222,170,0.4); border-radius: 0 8px 8px 0; padding: 12px 14px; margin-bottom: 10px; }
.resp-input { width: 100%; background: #f8fffe; border: 1px solid #d0f0e8; border-radius: 8px; padding: 12px 14px; font-family: 'DM Sans', sans-serif; font-size: 14px; color: #1a3a32; outline: none; resize: vertical; min-height: 80px; }
.resp-card { background: #fff; border-radius: 12px; padding: 24px; margin-bottom: 16px; border: 1px solid #e8f5f1; }
</style>
""", unsafe_allow_html=True)

# ── Mock data ──────────────────────────────────────────────────────────────────
random.seed(42); np.random.seed(42)
LOCATIONS = [("Nairobi",-1.286,36.817),("Kisumu",-0.091,34.768),("Mombasa",-4.043,39.668),("Nakuru",-0.303,36.080),("Eldoret",0.521,35.270),("Thika",-1.033,37.069),("Kitale",1.015,35.006),("Garissa",-0.453,39.646),("Nyeri",-0.416,36.947),("Kisii",-0.681,34.766),("Kakamega",0.282,34.752),("Isiolo",0.355,37.582)]
CHANNELS = ["WhatsApp","SMS","Email","QR Code"]
CHANNEL_COLORS = {"WhatsApp":"#4adeaa","SMS":"#2eb88a","Email":"#1d9e75","QR Code":"#0f6e56"}
THEMES = ["Water & Sanitation","Healthcare","Education","Transport","Security","Agriculture"]
VOICES = [
    ("We need better access to clean water. The borehole broke six months ago and nothing has been done.","Kisumu","WhatsApp","Water & Sanitation"),
    ("The clinic is too far and transport is expensive. Many mothers cannot reach it before delivery.","Nakuru","SMS","Healthcare"),
    ("Schools in our area have no toilets for girls. Daughters are staying home during their cycle.","Mombasa","Email","Education"),
    ("The roads to our farm are impassable during rain. We lose produce before it reaches the market.","Eldoret","QR Code","Transport"),
    ("There is no clean water for our children. We walk 5 km every morning to fetch water from the river.","Garissa","WhatsApp","Water & Sanitation"),
]

@st.cache_data
def load_mock_data():
    rows = []
    base_time = datetime.now() - timedelta(days=14)
    for i in range(500):
        loc = random.choice(LOCATIONS)
        ch = random.choices(CHANNELS, weights=[52,24,15,9])[0]
        theme = random.choices(THEMES, weights=[35,25,18,12,6,4])[0]
        ts = base_time + timedelta(days=random.uniform(0,14), hours=random.uniform(6,22))
        rows.append({"ID":f"Anon #{4000+i}","Location":loc[0],"Lat":loc[1]+random.uniform(-0.3,0.3),"Lon":loc[2]+random.uniform(-0.3,0.3),"Channel":ch,"Theme":theme,"Timestamp":ts,"Verified":random.random()>0.02,"Format":random.choices(["Text","Voice note","Photo"],weights=[60,25,15])[0]})
    return pd.DataFrame(rows).sort_values("Timestamp",ascending=False).reset_index(drop=True)

@st.cache_data
def make_timeseries():
    base = datetime.now()-timedelta(days=13)
    days,counts,total=[],[],0
    for i in range(14):
        c=int(np.random.normal(800+i*60,80)); total+=max(c,100)
        days.append((base+timedelta(days=i)).strftime("%b %d")); counts.append(total)
    return pd.DataFrame({"Date":days,"Responses":counts})

PB = dict(paper_bgcolor="rgba(13,51,44,1)",plot_bgcolor="rgba(13,51,44,1)",font=dict(family="DM Sans",color="#e8f5f1"),margin=dict(l=0,r=0,t=36,b=0))

def logo_html(size=26):
    return f"""<div style='display:flex;align-items:center;gap:10px;margin-bottom:20px;'>
    <div style='width:{size}px;height:{size}px;background:#4adeaa;border-radius:50%;box-shadow:0 0 10px rgba(74,222,170,0.5);'></div>
    <div><div style='font-size:{size-2}px;font-weight:300;color:#fff;letter-spacing:-0.5px;'>simu</div>
    <div style='font-size:10px;color:rgba(74,222,170,0.6);letter-spacing:0.5px;'>by Sakaza Afrika</div></div></div>"""

def step_bar(current, total=3):
    pips = ""
    for i in range(1, total+1):
        cls = "active" if i == current else ("done" if i < current else "step-pip")
        if i == current: cls = "step-pip active"
        elif i < current: cls = "step-pip done"
        else: cls = "step-pip"
        pips += f"<div class='{cls}'></div>"
    return f"<div class='step-bar'>{pips}</div><div style='font-size:11px;color:rgba(232,245,241,0.4);margin-bottom:20px;'>Step {current} of {total}</div>"

# ══════════════════════════════════════════════════════════════════════════════
# RESPONDENT PAGE (public)
# ══════════════════════════════════════════════════════════════════════════════
def show_respondent_page(slug):
    # Light theme for respondents
    st.markdown("""
    <style>
    .stApp { background-color: #f0faf6 !important; color: #1a3a32 !important; }
    section[data-testid="stSidebar"] { display: none !important; }
    div[data-testid="stTextInput"] input { background: #fff !important; border: 1px solid #c8ead8 !important; color: #1a3a32 !important; }
    div[data-baseweb="base-input"] { background: #fff !important; }
    div[data-baseweb="base-input"] input { color: #1a3a32 !important; }
    textarea { background: #fff !important; color: #1a3a32 !important; border: 1px solid #c8ead8 !important; }
    .stButton button { background: #1d9e75 !important; color: #fff !important; font-size: 15px !important; padding: 14px !important; }
    h1, h2, h3 { color: #1a3a32 !important; }
    </style>
    """, unsafe_allow_html=True)

    # Try to load campaign from Supabase
    campaign = None
    try:
        result = supabase_request("GET", f"campaigns?slug=eq.{slug}&is_live=eq.true")
        if isinstance(result, list) and result:
            campaign = result[0]
    except: pass

    _,col,_ = st.columns([1,2,1])
    with col:
        st.markdown("<br>", unsafe_allow_html=True)
        # Header
        st.markdown(f"""
        <div style='text-align:center;margin-bottom:32px;'>
            <div style='width:44px;height:44px;background:#1d9e75;border-radius:50%;margin:0 auto 14px;'></div>
            <div style='font-size:13px;color:#1d9e75;font-weight:500;letter-spacing:0.5px;margin-bottom:6px;'>
                {campaign.get('organisation','') if campaign else 'simu by Sakaza Afrika'}
            </div>
            <div style='font-size:26px;font-weight:600;color:#1a3a32;letter-spacing:-0.5px;margin-bottom:8px;'>
                {campaign.get('name','Share your voice') if campaign else 'Share your voice'}
            </div>
            <div style='font-size:14px;color:#4a7a6a;line-height:1.6;max-width:400px;margin:0 auto;'>
                {campaign.get('description','Your voice matters. Share your experience and help shape decisions for your community.') if campaign else 'Your voice matters. Share your experience and help shape decisions for your community.'}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Get prompts
        prompts = []
        if campaign and campaign.get('prompts'):
            prompts = campaign['prompts']
        else:
            prompts = [
                "Tell us what's happening in your community. What's the biggest challenge you face?",
                "How has this affected you or your family?",
                "What change would make the biggest difference?",
            ]

        with st.form("respondent_form"):

            # ── Story prompts ─────────────────────────────────────────────────
            st.markdown("""
            <div style='background:#fff;border-radius:12px;padding:24px;margin-bottom:16px;border:1px solid #d8f0e8;'>
                <div style='font-size:13px;font-weight:500;color:#1d9e75;letter-spacing:0.5px;text-transform:uppercase;margin-bottom:16px;'>Your story</div>
            """, unsafe_allow_html=True)

            answers = []
            for i, prompt in enumerate(prompts):
                st.markdown(f"""
                <div style='margin-bottom:6px;'>
                    <span style='font-size:12px;font-weight:600;color:#1d9e75;'>Q{i+1}</span>
                    <span style='font-size:14px;font-weight:500;color:#1a3a32;margin-left:8px;'>{prompt}</span>
                </div>
                """, unsafe_allow_html=True)
                answer = st.text_area("", placeholder="Write your answer here...", key=f"q_{i}", label_visibility="collapsed")
                answers.append(answer)
                st.markdown("<br>", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

            # ── Location ──────────────────────────────────────────────────────
            st.markdown("""
            <div style='background:#fff;border-radius:12px;padding:20px;margin-bottom:16px;border:1px solid #d8f0e8;'>
                <div style='font-size:13px;font-weight:500;color:#1d9e75;letter-spacing:0.5px;text-transform:uppercase;margin-bottom:12px;'>Your location</div>
            """, unsafe_allow_html=True)
            location = st.text_input("Town, county or region", placeholder="e.g. Kisumu, Kenya", label_visibility="visible")
            st.markdown("</div>", unsafe_allow_html=True)

            # ── Contact details (optional) ────────────────────────────────────
            st.markdown("""
            <div style='background:#fff;border-radius:12px;padding:20px;margin-bottom:16px;border:1px solid #d8f0e8;'>
                <div style='font-size:13px;font-weight:500;color:#1d9e75;letter-spacing:0.5px;text-transform:uppercase;margin-bottom:4px;'>Contact details</div>
                <div style='font-size:12px;color:#6a9a8a;margin-bottom:14px;'>Optional — but helps us follow up and grow our community.</div>
            """, unsafe_allow_html=True)
            contact_name = st.text_input("Full name", placeholder="e.g. Amina Wanjiru", label_visibility="visible")
            col_ph, col_em = st.columns(2)
            with col_ph:
                phone = st.text_input("Phone number", placeholder="e.g. +254 700 000 000", label_visibility="visible")
            with col_em:
                email = st.text_input("Email address", placeholder="e.g. amina@email.com", label_visibility="visible")
            st.markdown("</div>", unsafe_allow_html=True)

            # ── Permissions (required) ────────────────────────────────────────
            st.markdown("""
            <div style='background:#fff;border-radius:12px;padding:20px;margin-bottom:20px;border:1px solid #d8f0e8;'>
                <div style='font-size:13px;font-weight:500;color:#1d9e75;letter-spacing:0.5px;text-transform:uppercase;margin-bottom:14px;'>Permissions <span style='color:#e05a5a;'>*</span></div>
            """, unsafe_allow_html=True)

            org_name = campaign.get('organisation', 'the campaign team') if campaign else 'the campaign team'
            perm_media = st.checkbox(
                f"I give permission for my story, photos, and voice recordings to be used and shared by {org_name} for campaign and advocacy purposes.",
                value=False
            )
            perm_contact = st.checkbox(
                f"I agree to be contacted by {org_name} about this campaign and related updates. I can opt out at any time.",
                value=False
            )
            st.markdown("""
            <div style='font-size:11px;color:#8aaa9a;margin-top:10px;line-height:1.6;'>
                Your data is handled in accordance with applicable data protection laws including POPIA and GDPR.
                You can request removal of your data at any time by contacting the campaign team.
            </div>
            </div>
            """, unsafe_allow_html=True)

            submitted = st.form_submit_button("Submit my story →", use_container_width=True)

            if submitted:
                if not any(answers) or not location:
                    st.error("Please answer at least one question and share your location.")
                elif not perm_media or not perm_contact:
                    st.error("Please tick both permission boxes before submitting.")
                else:
                    if campaign:
                        try:
                            response_data = {
                                "campaign_id": campaign['id'],
                                "respondent_id": contact_name if contact_name else f"Anon #{random.randint(1000,9999)}",
                                "location": location,
                                "content": " | ".join([f"Q{i+1}: {a}" for i,a in enumerate(answers) if a]),
                                "channel": "Web link",
                                "verified": True,
                                "format": "Text",
                            }
                            supabase_request("POST", "responses", response_data)
                            # Save contact details if provided
                            if contact_name or phone or email:
                                contact_data = {
                                    "campaign_id": campaign['id'],
                                    "name": contact_name,
                                    "phone": phone,
                                    "email": email,
                                    "location": location,
                                    "perm_media": perm_media,
                                    "perm_contact": perm_contact,
                                }
                                supabase_request("POST", "contacts", contact_data)
                        except: pass

                    st.markdown("""
                    <div style='background:#1d9e75;border-radius:12px;padding:28px;text-align:center;margin-top:16px;'>
                        <div style='font-size:32px;margin-bottom:12px;'>✓</div>
                        <div style='font-size:20px;font-weight:600;color:#fff;margin-bottom:8px;'>Thank you.</div>
                        <div style='font-size:14px;color:rgba(255,255,255,0.8);line-height:1.6;'>
                            Your voice has been received and verified.<br>It will help shape real decisions for your community.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("""
        <div style='text-align:center;margin-top:24px;'>
            <div style='font-size:11px;color:#4a7a6a;'>Powered by</div>
            <div style='font-size:14px;font-weight:500;color:#1d9e75;'>simu by Sakaza Afrika</div>
        </div>
        """, unsafe_allow_html=True)

def show_reset_password():
    _,col,_ = st.columns([1,1.2,1])
    with col:
        st.markdown("<br><br>",unsafe_allow_html=True)
        st.markdown(logo_html(32),unsafe_allow_html=True)
        st.markdown("<div style='font-size:22px;font-weight:500;color:#fff;margin-bottom:4px;'>Set new password</div><div style='font-size:13px;color:rgba(232,245,241,0.4);margin-bottom:24px;'>Choose a new password for your account.</div>",unsafe_allow_html=True)
        with st.form("reset_password_form"):
            new_password = st.text_input("New password", type="password", placeholder="At least 8 characters")
            confirm_password = st.text_input("Confirm password", type="password", placeholder="Repeat your new password")
            st.markdown("<br>",unsafe_allow_html=True)
            submitted = st.form_submit_button("Set new password", use_container_width=True)
            if submitted:
                if not new_password or not confirm_password:
                    st.error("Please fill in both fields.")
                elif len(new_password) < 8:
                    st.error("Password must be at least 8 characters.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    try:
                        token = st.session_state.get("reset_token")
                        with httpx.Client() as client:
                            r = client.put(
                                f"{SUPABASE_URL}/auth/v1/user",
                                headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                                json={"password": new_password}
                            )
                        if r.status_code == 200:
                            st.success("Password updated! You can now log in.")
                            st.session_state.auth_page = "login"
                            st.rerun()
                        else:
                            st.error("Something went wrong. Please try again.")
                    except Exception as e:
                        st.error(f"Error: {e}")
# ══════════════════════════════════════════════════════════════════════════════
# LANDING
# ══════════════════════════════════════════════════════════════════════════════
def show_landing():
    _,col,_ = st.columns([1,2,1])
    with col:
        st.markdown("<br><br>",unsafe_allow_html=True)
        st.markdown(logo_html(48),unsafe_allow_html=True)
        st.markdown("""<div style='font-family:"DM Serif Display",serif;font-size:44px;font-weight:400;color:#fff;line-height:1.15;letter-spacing:-1px;margin-bottom:16px;'>Every voice<br>has a channel.</div>
        <div style='font-size:16px;color:rgba(232,245,241,0.55);line-height:1.6;margin-bottom:36px;'>Collect authentic community voices at scale — via WhatsApp, SMS, email or QR code. Verified. Structured. Ready to use.</div>""",unsafe_allow_html=True)
        b1,b2 = st.columns(2)
        with b1:
            if st.button("Get started free",use_container_width=True):
                st.session_state.auth_page="signup"; st.rerun()
        with b2:
            if st.button("Log in",use_container_width=True):
                st.session_state.auth_page="login"; st.rerun()
        st.markdown("<br>",unsafe_allow_html=True)
        st.markdown("""<div style='display:flex;gap:32px;flex-wrap:wrap;'>
        <div><div style='font-size:20px;font-weight:500;color:#4adeaa;'>20 → 200k</div><div style='font-size:11px;color:rgba(232,245,241,0.4);'>responses at any scale</div></div>
        <div><div style='font-size:20px;font-weight:500;color:#4adeaa;'>4 channels</div><div style='font-size:11px;color:rgba(232,245,241,0.4);'>WhatsApp, SMS, Email, QR</div></div>
        <div><div style='font-size:20px;font-weight:500;color:#4adeaa;'>99%</div><div style='font-size:11px;color:rgba(232,245,241,0.4);'>verified submissions</div></div>
        </div>""",unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SIGN UP
# ══════════════════════════════════════════════════════════════════════════════
def show_signup():
    _,col,_ = st.columns([1,1.2,1])
    with col:
        st.markdown("<br><br>",unsafe_allow_html=True)
        st.markdown(logo_html(32),unsafe_allow_html=True)
        st.markdown("<div style='font-size:22px;font-weight:500;color:#fff;margin-bottom:4px;'>Create your account</div><div style='font-size:13px;color:rgba(232,245,241,0.4);margin-bottom:24px;'>Start collecting voices today.</div>",unsafe_allow_html=True)
        with st.form("signup_form"):
            name = st.text_input("Full name",placeholder="Nelisa Dube")
            org = st.text_input("Organisation",placeholder="Sakaza Afrika")
            email = st.text_input("Email address",placeholder="you@organisation.com")
            password = st.text_input("Password",type="password",placeholder="At least 8 characters")
            st.markdown("<br>",unsafe_allow_html=True)
            submitted = st.form_submit_button("Create account",use_container_width=True)
            if submitted:
                if not all([name,org,email,password]): st.error("Please fill in all fields.")
                elif len(password)<8: st.error("Password must be at least 8 characters.")
                else:
                    try:
                        auth=get_auth_client()
                        res=auth.sign_up({"email":email,"password":password})
                        if res.user:
                            st.session_state.user=res.user
                            st.session_state.access_token=res.session.access_token if res.session else None
                            st.session_state.user_name=name; st.session_state.user_org=org
                            st.session_state.auth_page="create_campaign"; st.session_state.campaign_step=1
                            st.rerun()
                        else: st.error("Sign up failed. Please try again.")
                    except Exception as e: st.error(f"Error: {e}")
        st.markdown("<div style='text-align:center;margin-top:16px;font-size:13px;color:rgba(232,245,241,0.4);'>Already have an account?</div>",unsafe_allow_html=True)
        if st.button("Log in instead",use_container_width=True):
            st.session_state.auth_page="login"; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════════════════════════════════════
def show_login():
    _,col,_ = st.columns([1,1.2,1])
    with col:
        st.markdown("<br><br>",unsafe_allow_html=True)
        st.markdown(logo_html(32),unsafe_allow_html=True)
        st.markdown("<div style='font-size:22px;font-weight:500;color:#fff;margin-bottom:4px;'>Welcome back</div><div style='font-size:13px;color:rgba(232,245,241,0.4);margin-bottom:24px;'>Log in to your simu account</div>",unsafe_allow_html=True)
        with st.form("login_form"):
            email = st.text_input("Email address",placeholder="you@organisation.com")
            password = st.text_input("Password",type="password",placeholder="Your password")
            st.markdown("<br>",unsafe_allow_html=True)
            submitted = st.form_submit_button("Log in",use_container_width=True)
            if submitted:
                if not email or not password: st.error("Please enter your email and password.")
                else:
                    try:
                        auth=get_auth_client()
                        res=auth.sign_in_with_password({"email":email,"password":password})
                        if res.user:
                            st.session_state.user=res.user
                            st.session_state.access_token=res.session.access_token
                            st.session_state.auth_page="dashboard"; st.rerun()
                        else: st.error("Incorrect email or password.")
                    except: st.error("Incorrect email or password. If you just signed up, check your email to confirm your account first.")
        st.markdown("<div style='text-align:center;margin-top:12px;font-size:13px;color:rgba(232,245,241,0.4);'>Forgot your password?</div>",unsafe_allow_html=True)
        with st.expander("Reset password"):
            with st.form("reset_form"):
                reset_email = st.text_input("Enter your email address", placeholder="you@organisation.com")
                reset_btn = st.form_submit_button("Send reset link", use_container_width=True)
                if reset_btn:
                    if not reset_email: st.error("Please enter your email address.")
                    else:
                        try:
                            with httpx.Client() as client:
                                client.post(
                                    f"{SUPABASE_URL}/auth/v1/recover",
                                    headers={"apikey": SUPABASE_KEY, "Content-Type": "application/json"},
                                    json={"email": reset_email}
                                )
                            st.success(f"Password reset link sent to {reset_email} — check your inbox.")
                        except: st.success(f"If that email exists, a reset link has been sent.")
        st.markdown("<div style='text-align:center;margin-top:16px;font-size:13px;color:rgba(232,245,241,0.4);'>Don't have an account?</div>",unsafe_allow_html=True)
        if st.button("Sign up free",use_container_width=True):
            st.session_state.auth_page="signup"; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# CAMPAIGN CREATION — 3 STEPS
# ══════════════════════════════════════════════════════════════════════════════
def show_create_campaign():
    _,col,_ = st.columns([1,2,1])
    with col:
        st.markdown("<br>",unsafe_allow_html=True)
        st.markdown(logo_html(24),unsafe_allow_html=True)
        st.markdown(st.session_state.campaign_step and step_bar(st.session_state.campaign_step),unsafe_allow_html=True)

        draft = st.session_state.campaign_draft

        # ── STEP 1: Basics ────────────────────────────────────────────────────
        if st.session_state.campaign_step == 1:
            st.markdown("<div style='font-size:22px;font-weight:500;color:#fff;margin-bottom:4px;'>Campaign basics</div><div style='font-size:13px;color:rgba(232,245,241,0.4);margin-bottom:20px;'>Name your campaign and tell us who it's for.</div>",unsafe_allow_html=True)
            with st.form("step1_form"):
                campaign_name = st.text_input("Campaign name *", value=draft.get("name",""), placeholder="e.g. Community Water Access Survey")
                org = st.text_input("Organisation *", value=draft.get("organisation", st.session_state.get("user_org","")), placeholder="e.g. ActionAid Kenya")
                description = st.text_area("What is this campaign about? *", value=draft.get("description",""), placeholder="Tell respondents why their voice matters and what you'll do with their stories.", height=90)
                col_a,col_b = st.columns(2)
                with col_a: campaign_type = st.selectbox("Campaign type", ["Community reporting","Audience callout","Qualitative research","Campaign storytelling","Needs assessment"], index=["Community reporting","Audience callout","Qualitative research","Campaign storytelling","Needs assessment"].index(draft.get("campaign_type","Community reporting")))
                with col_b: target = st.selectbox("Target responses", ["20 – 200","200 – 2,000","2,000 – 20,000","20,000+"])
                st.markdown("<br>",unsafe_allow_html=True)
                next1 = st.form_submit_button("Next: Channels →", use_container_width=True)
                if next1:
                    if not campaign_name or not org or not description:
                        st.error("Please fill in the campaign name, organisation and description.")
                    else:
                        st.session_state.campaign_draft.update({"name":campaign_name,"organisation":org,"description":description,"campaign_type":campaign_type,"target_responses":target})
                        st.session_state.campaign_step = 2; st.rerun()

        # ── STEP 2: Channels & formats ────────────────────────────────────────
        elif st.session_state.campaign_step == 2:
            st.markdown("<div style='font-size:22px;font-weight:500;color:#fff;margin-bottom:4px;'>Channels & formats</div><div style='font-size:13px;color:rgba(232,245,241,0.4);margin-bottom:20px;'>How will people reach simu? Every channel flows into one dashboard.</div>",unsafe_allow_html=True)
            with st.form("step2_form"):
                st.markdown('<div style="font-size:12px;font-weight:500;color:rgba(74,222,170,0.8);letter-spacing:0.8px;text-transform:uppercase;margin-bottom:10px;">Submission channels</div>',unsafe_allow_html=True)
                c1,c2,c3,c4 = st.columns(4)
                with c1: ch_wa = st.checkbox("WhatsApp", value=True)
                with c2: ch_sms = st.checkbox("SMS", value=True)
                with c3: ch_email = st.checkbox("Email", value=True)
                with c4: ch_qr = st.checkbox("QR Code")

                st.markdown('<div style="font-size:12px;font-weight:500;color:rgba(74,222,170,0.8);letter-spacing:0.8px;text-transform:uppercase;margin:16px 0 10px;">Accepted formats</div>',unsafe_allow_html=True)
                f1,f2,f3 = st.columns(3)
                with f1: fmt_text = st.checkbox("Text", value=True)
                with f2: fmt_voice = st.checkbox("Voice note", value=True)
                with f3: fmt_photo = st.checkbox("Photo")

                col_a,col_b = st.columns(2)
                with col_a: language = st.selectbox("Language", ["English","Swahili","French","Amharic","Zulu","Yoruba","Hausa"])
                with col_b: loc_tag = st.selectbox("Location tagging", ["Required","Optional","Disabled"])

                st.markdown("<br>",unsafe_allow_html=True)
                back2,next2 = st.columns(2)
                with back2: back_btn = st.form_submit_button("← Back", use_container_width=True)
                with next2: next_btn = st.form_submit_button("Next: Story prompts →", use_container_width=True)

                if back_btn:
                    st.session_state.campaign_step = 1; st.rerun()
                if next_btn:
                    channels = [c for c,v in [("WhatsApp",ch_wa),("SMS",ch_sms),("Email",ch_email),("QR Code",ch_qr)] if v]
                    formats = [f for f,v in [("Text",fmt_text),("Voice note",fmt_voice),("Photo",fmt_photo)] if v]
                    if not channels: st.error("Please select at least one channel.")
                    else:
                        st.session_state.campaign_draft.update({"channels":channels,"formats":formats,"language":language,"location_tagging":loc_tag})
                        st.session_state.campaign_step = 3; st.rerun()

        # ── STEP 3: Story prompts ─────────────────────────────────────────────
        elif st.session_state.campaign_step == 3:
            st.markdown("<div style='font-size:22px;font-weight:500;color:#fff;margin-bottom:4px;'>Story prompts</div><div style='font-size:13px;color:rgba(232,245,241,0.4);margin-bottom:20px;'>What do you want to ask respondents? Clear prompts get richer responses.</div>",unsafe_allow_html=True)

            # Manage prompts in session state
            if "prompts_list" not in st.session_state:
                st.session_state.prompts_list = draft.get("prompts", [
                    "Tell us what's happening in your community. What's the biggest challenge you face every day?",
                    "How has this affected you or your family?",
                ])

            # Show existing prompts
            to_remove = None
            for i, prompt in enumerate(st.session_state.prompts_list):
                col_p, col_x = st.columns([10,1])
                with col_p:
                    st.markdown(f"""
                    <div class='prompt-block'>
                        <div style='font-size:11px;color:rgba(74,222,170,0.6);font-weight:500;margin-bottom:4px;'>Q{i+1}</div>
                        <div style='font-size:13px;color:rgba(232,245,241,0.8);'>{prompt}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_x:
                    if st.button("✕", key=f"remove_{i}"):
                        to_remove = i

            if to_remove is not None:
                st.session_state.prompts_list.pop(to_remove); st.rerun()

            # Add new prompt
            st.markdown("<br>",unsafe_allow_html=True)
            st.markdown("""<style>
            .add-prompt-btn button { background: rgba(74,222,170,0.08) !important; color: #4adeaa !important; border: 1px dashed rgba(74,222,170,0.4) !important; font-weight: 400 !important; }
            .add-prompt-btn button:hover { background: rgba(74,222,170,0.15) !important; border-color: #4adeaa !important; }
            </style>""", unsafe_allow_html=True)
            with st.form("add_prompt_form"):
                new_prompt = st.text_input("Add a story prompt", placeholder="e.g. Where are you located?", label_visibility="visible")
                st.markdown('<div class="add-prompt-btn">', unsafe_allow_html=True)
                add_btn = st.form_submit_button("+ Add prompt", use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                if add_btn and new_prompt.strip():
                    st.session_state.prompts_list.append(new_prompt.strip()); st.rerun()

            st.markdown("<br>",unsafe_allow_html=True)
            st.markdown('<div style="font-size:12px;font-weight:500;color:rgba(74,222,170,0.8);letter-spacing:0.8px;text-transform:uppercase;margin-bottom:6px;">Closing message</div>', unsafe_allow_html=True)
            closing = st.text_area("", value=draft.get("closing_message","Thank you — your voice will shape real decisions for your community."), height=70, placeholder="Thank respondents and tell them what happens next.", label_visibility="collapsed")

            st.markdown("---",unsafe_allow_html=True)

            back3, launch = st.columns(2)
            with back3:
                if st.button("← Back", use_container_width=True):
                    st.session_state.campaign_step = 2; st.rerun()
            with launch:
                if st.button("Go live now", use_container_width=True):
                    if not st.session_state.prompts_list:
                        st.error("Please add at least one story prompt.")
                    else:
                        import re
                        name = draft.get("name","campaign")
                        slug = f"{re.sub(r'[^a-z0-9]+','-',name.lower()).strip('-')}-{random.randint(1000,9999)}"
                        campaign_data = {**draft, "user_id": st.session_state.user.id, "slug": slug, "is_live": True, "prompts": st.session_state.prompts_list, "closing_message": closing}
                        try:
                            result = supabase_request("POST","campaigns",campaign_data,st.session_state.access_token)
                            st.session_state.current_campaign = result[0] if isinstance(result,list) and result else campaign_data
                        except: st.session_state.current_campaign = campaign_data
                        st.session_state.current_campaign["slug"] = slug
                        st.session_state.show_launch = True
                        st.session_state.campaign_draft = {}
                        st.session_state.prompts_list = []
                        st.session_state.auth_page = "dashboard"
                        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# LAUNCH CONFIRMATION
# ══════════════════════════════════════════════════════════════════════════════
def show_launch_confirmation():
    campaign = st.session_state.current_campaign or {}
    name = campaign.get("name","Your campaign")
    slug = campaign.get("slug","your-campaign")
    local_link = f"http://localhost:8501/?c={slug}"
    live_link = f"simubysakaza.com/c/{slug}"

    _,col,_ = st.columns([1,2,1])
    with col:
        st.markdown("<br><br>",unsafe_allow_html=True)
        st.markdown(f"""
        <div style='text-align:center;margin-bottom:32px;'>
            <div style='width:72px;height:72px;background:#4adeaa;border-radius:50%;
            box-shadow:0 0 0 16px rgba(74,222,170,0.1),0 0 0 32px rgba(74,222,170,0.05);
            margin:0 auto 24px;display:flex;align-items:center;justify-content:center;font-size:32px;'>✓</div>
            <div style='font-family:"DM Serif Display",serif;font-size:34px;color:#fff;margin-bottom:8px;letter-spacing:-0.5px;'>Your campaign is live.</div>
            <div style='font-size:14px;color:rgba(232,245,241,0.5);'>{name} is ready to receive voices.</div>
        </div>
        """,unsafe_allow_html=True)

        st.markdown("""<div style='background:#0d332c;border:1px solid rgba(74,222,170,0.2);border-radius:10px;padding:20px;margin-bottom:16px;'>
        <div style='font-size:10px;letter-spacing:1px;text-transform:uppercase;color:rgba(74,222,170,0.5);margin-bottom:10px;'>Test link (local)</div>""",unsafe_allow_html=True)
        st.code(local_link, language=None)
        st.markdown(f"""<div style='font-size:12px;color:rgba(232,245,241,0.35);margin-top:6px;margin-bottom:16px;'>Use this to test the respondent experience right now. Open it in a new tab.</div>
        <div style='font-size:10px;letter-spacing:1px;text-transform:uppercase;color:rgba(74,222,170,0.5);margin-bottom:10px;'>Live link (once deployed)</div>""",unsafe_allow_html=True)
        st.code(live_link, language=None)
        st.markdown("""<div style='font-size:12px;color:rgba(232,245,241,0.35);margin-top:6px;'>This is the link to share with respondents once your campaign is ready to go live.</div>
        </div>""",unsafe_allow_html=True)

        st.markdown("<br>",unsafe_allow_html=True)

        if st.button("Open dashboard →", use_container_width=True):
            st.session_state.show_launch = False; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
def show_dashboard():
    ts_df=make_timeseries()
    campaigns=[]
    try:
        campaigns=supabase_request("GET",f"campaigns?user_id=eq.{st.session_state.user.id}&order=created_at.desc",token=st.session_state.access_token)
        if not isinstance(campaigns,list): campaigns=[]
    except: campaigns=[]

    # Use real campaign name if available
    campaign_name=""; campaign_org=""
    if campaigns:
        campaign_name=campaigns[0].get("name","")
        campaign_org=campaigns[0].get("organisation","")
    elif st.session_state.current_campaign:
        campaign_name=st.session_state.current_campaign.get("name","")
        campaign_org=st.session_state.current_campaign.get("organisation","")

    # Try to load real responses; fall back to mock only if no real campaigns
    real_responses=[]
    has_real_data = False
    if campaigns:
        try:
            cid = campaigns[0].get("id")
            real_responses = supabase_request("GET", f"responses?campaign_id=eq.{cid}&order=submitted_at.desc", token=st.session_state.access_token)
            if isinstance(real_responses, list) and len(real_responses) > 0:
                has_real_data = True
        except: pass

    if has_real_data:
        df = pd.DataFrame(real_responses)
        df = df.rename(columns={"respondent_id":"ID","submitted_at":"Timestamp"})
        if "Timestamp" in df.columns:
            df["Timestamp"] = pd.to_datetime(df["Timestamp"])
        if "verified" in df.columns:
            df = df.rename(columns={"verified":"Verified"})
    else:
        df = load_mock_data()

    with st.sidebar:
        st.markdown(logo_html(24),unsafe_allow_html=True)
        st.markdown('<div class="section-label">Navigation</div>',unsafe_allow_html=True)
        page=st.radio("",["Overview","Responses","Voices","Map","Analytics","Reporting"],label_visibility="collapsed")
        st.markdown("---")
        if campaign_name:
            st.markdown(f"""<div style='background:rgba(74,222,170,0.08);border:1px solid rgba(74,222,170,0.2);border-radius:8px;padding:12px 14px;margin-bottom:16px;'>
            <div style='font-size:13px;font-weight:500;color:#e8f5f1;margin-bottom:3px;'>{campaign_name}</div>
            <div style='font-size:11px;color:rgba(74,222,170,0.6);'>{campaign_org}</div>
            <div style='margin-top:8px;'><span class='live-dot'></span><span style='font-size:11px;color:#4adeaa;font-weight:500;'>LIVE</span></div>
            </div>""",unsafe_allow_html=True)
        st.markdown('<div class="section-label">Filter by channel</div>',unsafe_allow_html=True)
        selected_channels=st.multiselect("",CHANNELS,default=CHANNELS,label_visibility="collapsed")
        st.markdown('<div class="section-label" style="margin-top:12px;">Filter by theme</div>',unsafe_allow_html=True)
        selected_themes=st.multiselect("",THEMES,default=THEMES,label_visibility="collapsed")
        st.markdown("---")
        user_email=st.session_state.user.email if st.session_state.user else ""
        st.markdown(f'<div style="font-size:11px;color:rgba(232,245,241,0.35);margin-bottom:8px;">{user_email}</div>',unsafe_allow_html=True)
        if st.button("+ New campaign"):
            st.session_state.auth_page="create_campaign"; st.session_state.campaign_step=1; st.session_state.campaign_draft={}; st.rerun()
        if st.button("Log out"):
            st.session_state.user=None; st.session_state.access_token=None; st.session_state.auth_page="landing"; st.rerun()

    # Apply filters only if columns exist
    if "Channel" in df.columns and "Theme" in df.columns:
        filtered=df[df["Channel"].isin(selected_channels)&df["Theme"].isin(selected_themes)].copy()
    else:
        filtered=df.copy()

    if page=="Overview":
        c1,c2=st.columns([3,1])
        with c1:
            st.markdown(f'<div class="section-label">Campaign overview</div>',unsafe_allow_html=True)
            st.markdown(f'<div class="campaign-title">{campaign_name or "Your dashboard"}</div>',unsafe_allow_html=True)
            st.markdown(f'<div class="campaign-meta">{campaign_org}</div>',unsafe_allow_html=True)
        with c2:
            st.markdown("<div style='text-align:right;padding-top:12px;'><span class='live-dot'></span><span style='font-size:13px;color:#4adeaa;font-weight:500;'>LIVE</span></div>",unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)

        if not not has_real_data and not campaigns:
            st.markdown("""<div style='background:#0d332c;border:1px solid rgba(74,222,170,0.15);border-radius:10px;padding:40px;text-align:center;margin:20px 0;'>
            <div style='font-size:32px;margin-bottom:12px;'>📭</div>
            <div style='font-size:18px;font-weight:500;color:#fff;margin-bottom:8px;'>No responses yet</div>
            <div style='font-size:13px;color:rgba(232,245,241,0.4);'>Share your campaign link to start collecting voices.</div>
            </div>""", unsafe_allow_html=True)
        else:
            total = len(filtered) if has_real_data else len(filtered)
            m1,m2,m3,m4=st.columns(4)
            m1.metric("Total responses",f"{total:,}")
            m2.metric("Verified",f"{filtered['Verified'].mean():.0%}" if 'Verified' in filtered.columns else "—")
            m3.metric("Locations",f"{filtered['Location'].nunique()}" if 'Location' in filtered.columns else "—")
            m4.metric("Avg. response time","—" if has_real_data else "2 min")
            st.markdown("<br>",unsafe_allow_html=True)

            if not has_real_data:
                a,b=st.columns([2,1])
                with a:
                    fig=go.Figure(); fig.add_trace(go.Scatter(x=ts_df["Date"],y=ts_df["Responses"],mode="lines",fill="tozeroy",line=dict(color="#4adeaa",width=2.5),fillcolor="rgba(74,222,170,0.1)"))
                    fig.update_layout(title=dict(text="Responses over time",font=dict(size=13,color="rgba(232,245,241,0.6)"),x=0),xaxis=dict(showgrid=False,tickfont=dict(size=11,color="rgba(232,245,241,0.4)")),yaxis=dict(showgrid=True,gridcolor="rgba(74,222,170,0.07)",tickfont=dict(size=11,color="rgba(232,245,241,0.4)")),height=220,**PB)
                    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
                with b:
                    cc=filtered["Channel"].value_counts()
                    fig2=go.Figure(go.Pie(labels=cc.index,values=cc.values,hole=0.65,marker=dict(colors=["#4adeaa","#2eb88a","#1d9e75","#0f6e56"]),textinfo="none"))
                    fig2.add_annotation(text=f"<b>{len(filtered):,}</b>",x=0.5,y=0.5,font=dict(size=16,color="#fff"),showarrow=False)
                    fig2.update_layout(title=dict(text="By channel",font=dict(size=13,color="rgba(232,245,241,0.6)"),x=0),legend=dict(font=dict(size=11,color="rgba(232,245,241,0.6)"),bgcolor="rgba(0,0,0,0)"),height=220,**PB)
                    st.plotly_chart(fig2,use_container_width=True,config={"displayModeBar":False})
                c,d=st.columns([1,2])
                with c:
                    tc=filtered["Theme"].value_counts().reset_index(); tc.columns=["Theme","Count"]
                    fig3=go.Figure(go.Bar(y=tc["Theme"],x=tc["Count"],orientation="h",marker_color="#4adeaa",marker_opacity=0.85))
                    fig3.update_layout(title=dict(text="Top themes",font=dict(size=13,color="rgba(232,245,241,0.6)"),x=0),xaxis=dict(showgrid=True,gridcolor="rgba(74,222,170,0.07)",tickfont=dict(size=10,color="rgba(232,245,241,0.4)")),yaxis=dict(tickfont=dict(size=11,color="rgba(232,245,241,0.7)")),height=250,**PB)
                    st.plotly_chart(fig3,use_container_width=True,config={"displayModeBar":False})
                with d:
                    fig4=px.scatter_mapbox(filtered.head(300),lat="Lat",lon="Lon",color_discrete_sequence=["#4adeaa"],zoom=5,center={"lat":0.0,"lon":37.9},mapbox_style="carto-darkmatter",hover_data={"Location":True,"Theme":True,"Channel":True,"Lat":False,"Lon":False})
                    fig4.update_traces(marker=dict(size=7,opacity=0.7,color="#4adeaa"))
                    fig4.update_layout(title=dict(text="Response map",font=dict(size=13,color="rgba(232,245,241,0.6)"),x=0),height=250,**PB)
                    st.plotly_chart(fig4,use_container_width=True,config={"displayModeBar":False})

        st.markdown("---")
        st.markdown('<div class="section-label">Latest community voices</div>',unsafe_allow_html=True)
        if has_real_data and "content" in filtered.columns:
            for _,row in filtered.head(4).iterrows():
                st.markdown(f'<div class="voice-card"><div class="voice-text">"{row.get("content","")}"</div><div class="voice-meta">📍 {row.get("location","—")} <span class="voice-badge">{row.get("channel","—")}</span> ✓ Verified</div></div>',unsafe_allow_html=True)
        else:
            for voice,loc,ch,theme in VOICES[:4]:
                st.markdown(f'<div class="voice-card"><div class="voice-text">"{voice}"</div><div class="voice-meta">📍 {loc}, Kenya <span class="voice-badge">{ch}</span> {theme} &nbsp;✓ Verified</div></div>',unsafe_allow_html=True)

    elif page=="Responses":
        st.markdown('<div class="section-label">All responses</div>',unsafe_allow_html=True)
        st.markdown(f'<div class="campaign-title">{len(filtered):,} submissions</div>',unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)
        s1,s2,s3=st.columns(3)
        with s1: search=st.text_input("Search location / theme",placeholder="e.g. Nairobi")
        with s2: ch_f=st.selectbox("Channel",["All"]+CHANNELS)
        with s3: th_f=st.selectbox("Theme",["All"]+THEMES)
        d2=filtered.copy()
        if search: d2=d2[d2["Location"].str.contains(search,case=False)|d2["Theme"].str.contains(search,case=False)]
        if ch_f!="All": d2=d2[d2["Channel"]==ch_f]
        if th_f!="All": d2=d2[d2["Theme"]==th_f]
        d2["Time"]=d2["Timestamp"].dt.strftime("%b %d, %H:%M"); d2["Verified"]=d2["Verified"].map({True:"✓",False:"✗"})
        st.dataframe(d2[["ID","Location","Channel","Theme","Format","Time","Verified"]].head(200),use_container_width=True,height=480,hide_index=True)
        csv2=d2[["ID","Location","Channel","Theme","Format","Time","Verified"]].to_csv(index=False).encode("utf-8")
        st.download_button("⬇  Export to CSV",data=csv2,file_name="simu_responses.csv",mime="text/csv")

    elif page=="Voices":
        st.markdown('<div class="section-label">Community voices</div>',unsafe_allow_html=True)
        st.markdown('<div class="campaign-title">Straight from the source.</div>',unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)
        v1,v2=st.columns(2)
        with v1: vt=st.selectbox("Filter by theme",["All"]+THEMES)
        with v2: vc=st.selectbox("Filter by channel",["All"]+CHANNELS)
        vshow=[v for v in VOICES if (vt=="All" or v[3]==vt) and (vc=="All" or v[2]==vc)] or VOICES[:2]
        for voice,loc,ch,theme in vshow:
            st.markdown(f'<div class="voice-card"><div class="voice-text">"{voice}"</div><div class="voice-meta">📍 {loc}, Kenya <span class="voice-badge">{ch}</span> {theme} &nbsp;<span style="color:#4adeaa;">✓ Verified</span></div></div>',unsafe_allow_html=True)

    elif page=="Map":
        st.markdown('<div class="section-label">Response map</div>',unsafe_allow_html=True)
        st.markdown('<div class="campaign-title">Where voices are coming from</div>',unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)
        color_by=st.radio("Colour by",["Channel","Theme"],horizontal=True)
        mc,ic=st.columns([3,1])
        with mc:
            pal=["#4adeaa","#2eb88a","#1d9e75","#0f6e56","#085041","#04342c"]
            fm=px.scatter_mapbox(filtered.head(400),lat="Lat",lon="Lon",color=color_by,color_discrete_sequence=pal,zoom=5,center={"lat":0.2,"lon":37.5},mapbox_style="carto-darkmatter",hover_data={"Location":True,"Theme":True,"Channel":True,"Lat":False,"Lon":False})
            fm.update_traces(marker=dict(size=9,opacity=0.75))
            fm.update_layout(legend=dict(font=dict(size=11,color="rgba(232,245,241,0.7)"),bgcolor="rgba(13,51,44,0.8)"),height=520,**PB)
            st.plotly_chart(fm,use_container_width=True,config={"displayModeBar":False})
        with ic:
            st.markdown('<div class="section-label">Top locations</div>',unsafe_allow_html=True)
            lc=filtered["Location"].value_counts().head(12).reset_index(); lc.columns=["Location","Count"]
            for _,row in lc.iterrows():
                pct=int(row["Count"]/len(filtered)*100)
                st.markdown(f'<div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid rgba(74,222,170,0.07);"><span style="font-size:12px;color:rgba(232,245,241,0.7);">📍 {row["Location"]}</span><span style="font-size:11px;background:rgba(74,222,170,0.08);color:rgba(74,222,170,0.7);padding:2px 7px;border-radius:3px;">{pct}%</span></div>',unsafe_allow_html=True)

    elif page=="Analytics":
        st.markdown('<div class="section-label">Analytics</div>',unsafe_allow_html=True)
        st.markdown('<div class="campaign-title">Deep dive</div>',unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)
        a1,a2=st.columns(2)
        with a1:
            filtered["Hour"]=filtered["Timestamp"].dt.hour; filtered["DayName"]=filtered["Timestamp"].dt.strftime("%a")
            heat=filtered.groupby(["DayName","Hour"]).size().reset_index(name="Count")
            hp=heat.pivot(index="DayName",columns="Hour",values="Count").reindex(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]).fillna(0)
            fh=px.imshow(hp,color_continuous_scale=[[0,"#0d332c"],[0.5,"#1d9e75"],[1,"#4adeaa"]],aspect="auto")
            fh.update_layout(title=dict(text="Activity heatmap",font=dict(size=13,color="rgba(232,245,241,0.6)"),x=0),coloraxis_showscale=False,height=250,**PB)
            st.plotly_chart(fh,use_container_width=True,config={"displayModeBar":False})
        with a2:
            fc=filtered["Format"].value_counts().reset_index(); fc.columns=["Format","Count"]
            ff=px.bar(fc,x="Format",y="Count",color_discrete_sequence=["#4adeaa"])
            ff.update_layout(title=dict(text="Submission formats",font=dict(size=13,color="rgba(232,245,241,0.6)"),x=0),xaxis=dict(showgrid=False,tickfont=dict(size=11,color="rgba(232,245,241,0.6)")),yaxis=dict(showgrid=True,gridcolor="rgba(74,222,170,0.07)"),showlegend=False,height=250,**PB)
            st.plotly_chart(ff,use_container_width=True,config={"displayModeBar":False})
        a3,a4=st.columns(2)
        with a3:
            tc2=filtered.groupby(["Theme","Channel"]).size().reset_index(name="Count")
            fs=px.bar(tc2,x="Theme",y="Count",color="Channel",color_discrete_map=CHANNEL_COLORS,barmode="stack")
            fs.update_layout(title=dict(text="Theme by channel",font=dict(size=13,color="rgba(232,245,241,0.6)"),x=0),xaxis=dict(showgrid=False,tickfont=dict(size=10,color="rgba(232,245,241,0.6)"),tickangle=-20),yaxis=dict(showgrid=True,gridcolor="rgba(74,222,170,0.07)"),legend=dict(font=dict(size=11,color="rgba(232,245,241,0.6)"),bgcolor="rgba(0,0,0,0)"),margin=dict(l=0,r=0,t=36,b=40),height=260,paper_bgcolor="rgba(13,51,44,1)",plot_bgcolor="rgba(13,51,44,1)",font=dict(family="DM Sans",color="#e8f5f1"))
            st.plotly_chart(fs,use_container_width=True,config={"displayModeBar":False})
        with a4:
            filtered["Date"]=filtered["Timestamp"].dt.date
            dc=filtered.groupby(["Date","Channel"]).size().reset_index(name="Count")
            fd=px.line(dc,x="Date",y="Count",color="Channel",color_discrete_map=CHANNEL_COLORS)
            fd.update_layout(title=dict(text="Channel trends",font=dict(size=13,color="rgba(232,245,241,0.6)"),x=0),xaxis=dict(showgrid=False,tickfont=dict(size=10,color="rgba(232,245,241,0.4)")),yaxis=dict(showgrid=True,gridcolor="rgba(74,222,170,0.07)"),legend=dict(font=dict(size=11,color="rgba(232,245,241,0.6)"),bgcolor="rgba(0,0,0,0)"),height=260,**PB)
            st.plotly_chart(fd,use_container_width=True,config={"displayModeBar":False})
        st.markdown("---")
        s1,s2,s3,s4,s5=st.columns(5)
        s1.metric("Total",f"{len(filtered):,}"); s2.metric("Verified",f"{filtered['Verified'].mean():.1%}")
        s3.metric("Locations",filtered["Location"].nunique()); s4.metric("Channels",filtered["Channel"].nunique()); s5.metric("Themes",filtered["Theme"].nunique())
    elif page=="Reporting":
        st.markdown('<div class="section-label">Reporting</div>',unsafe_allow_html=True)
        st.markdown('<div class="campaign-title">Export & share your data</div>',unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)
        st.markdown("""<div style='background:#0d332c;border:1px solid rgba(74,222,170,0.15);border-radius:10px;padding:24px;margin-bottom:16px;'>
        <div style='font-size:13px;font-weight:500;color:#4adeaa;margin-bottom:8px;'>CSV Export</div>
        <div style='font-size:13px;color:rgba(232,245,241,0.6);margin-bottom:16px;'>Download all responses as a spreadsheet. Ready to use in Excel, Google Sheets or any data tool.</div>
        </div>""",unsafe_allow_html=True)
        csv_all=filtered.to_csv(index=False).encode("utf-8")
        st.download_button("⬇  Download full CSV",data=csv_all,file_name="simu_responses.csv",mime="text/csv",use_container_width=True)
        st.markdown("<br>",unsafe_allow_html=True)
        st.markdown("""<div style='background:#0d332c;border:1px solid rgba(74,222,170,0.15);border-radius:10px;padding:24px;margin-bottom:16px;'>
        <div style='font-size:13px;font-weight:500;color:#4adeaa;margin-bottom:8px;'>Email report</div>
        <div style='font-size:13px;color:rgba(232,245,241,0.6);margin-bottom:16px;'>Send a summary report to your email address.</div>
        </div>""",unsafe_allow_html=True)
        report_email=st.text_input("Email address",placeholder="you@organisation.com")
        if st.button("Send report",use_container_width=True):
            if report_email:
                st.success(f"Report sent to {report_email}")
            else:
                st.error("Please enter an email address.")
# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════
params = st.query_params
try:
    import urllib.parse
    full_url = st.context.headers.get("referer","")
    if "#" in full_url:
        hash_part = full_url.split("#")[1]
        hash_params = dict(urllib.parse.parse_qsl(hash_part))
        if "access_token" in hash_params and hash_params.get("type") == "recovery":
            st.session_state.reset_token = hash_params["access_token"]
            st.session_state.auth_page = "reset_password"
except: pass

if "c" in params:
    show_respondent_page(params["c"])
elif st.session_state.auth_page == "reset_password":
    show_reset_password()
elif st.session_state.user is None:
    if st.session_state.auth_page=="signup": show_signup()
    elif st.session_state.auth_page=="login": show_login()
    else: show_landing()
else:
    if st.session_state.auth_page=="create_campaign": show_create_campaign()
    elif st.session_state.show_launch: show_launch_confirmation()
    else: show_dashboard()
