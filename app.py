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

import os
SUPABASE_URL = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY", "")
if SUPABASE_URL and not SUPABASE_URL.startswith("http"):
    SUPABASE_URL = f"https://{SUPABASE_URL}"
BASE_URL = "http://localhost:8501"

RESPOND_BASE = "https://simubysakaza.com/respond.html"

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

for k,v in [("user",None),("access_token",None),("auth_page","landing"),("current_campaign",None),("show_launch",False),("campaign_step",1),("campaign_draft",{})]:
    if k not in st.session_state: st.session_state[k] = v

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
input, input[type="text"], input[type="password"], input[type="email"] { color: #e8f5f1 !important; background-color: #0d332c !important; caret-color: #4adeaa !important; }
input:focus { background-color: #0d332c !important; color: #e8f5f1 !important; }
div[data-baseweb="base-input"] { background-color: #0d332c !important; border: 1px solid rgba(74,222,170,0.2) !important; border-radius: 6px !important; }
div[data-baseweb="base-input"] input { color: #e8f5f1 !important; background: transparent !important; -webkit-text-fill-color: #e8f5f1 !important; }
div[data-baseweb="base-input"] input::placeholder { color: rgba(232,245,241,0.3) !important; -webkit-text-fill-color: rgba(232,245,241,0.3) !important; }
div[data-baseweb="base-input"] input:-webkit-autofill,
div[data-baseweb="base-input"] input:-webkit-autofill:hover,
div[data-baseweb="base-input"] input:-webkit-autofill:focus { -webkit-text-fill-color: #e8f5f1 !important; -webkit-box-shadow: 0 0 0px 1000px #0d332c inset !important; transition: background-color 5000s ease-in-out 0s; }
textarea { color: #e8f5f1 !important; background-color: #0d332c !important; border: 1px solid rgba(74,222,170,0.2) !important; border-radius: 8px !important; }
textarea:focus { background-color: #0d332c !important; color: #e8f5f1 !important; }
div[data-testid="stTextInput"] label, div[data-testid="stTextArea"] label { color: rgba(232,245,241,0.6) !important; font-size: 12px !important; }
div[data-baseweb="base-input"], div[data-baseweb="base-input"] > div { background-color: #0d332c !important; }
div[data-baseweb="base-input"] input { color: #e8f5f1 !important; background: transparent !important; }
div[data-baseweb="select"] div { color: #e8f5f1 !important; background-color: rgba(255,255,255,0.04) !important; }
div[data-baseweb="select"] span { color: #e8f5f1 !important; }
div[data-testid="stSelectbox"] label { color: rgba(232,245,241,0.6) !important; }
.stButton button { background: #4adeaa !important; color: #0a2a24 !important; border: none !important; border-radius: 8px !important; font-weight: 600 !important; font-family: 'DM Sans', sans-serif !important; transition: all 0.2s !important; }
.stButton button:hover { background: #6be8bc !important; color: #0a2a24 !important; }
.stFormSubmitButton button { background: #4adeaa !important; color: #0a2a24 !important; border: none !important; border-radius: 8px !important; font-weight: 600 !important; font-family: 'DM Sans', sans-serif !important; }
.stFormSubmitButton button:hover { background: #6be8bc !important; color: #0a2a24 !important; }
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
.empty-state { background: rgba(74,222,170,0.04); border: 1px dashed rgba(74,222,170,0.2); border-radius: 12px; padding: 48px 32px; text-align: center; margin: 24px 0; }
.empty-state-icon { font-size: 36px; margin-bottom: 16px; }
.empty-state-title { font-size: 18px; font-weight: 500; color: #fff; margin-bottom: 8px; }
.empty-state-sub { font-size: 14px; color: rgba(232,245,241,0.4); line-height: 1.6; }
</style>
""", unsafe_allow_html=True)

CHANNELS = ["WhatsApp","SMS","Email","QR Code"]
CHANNEL_COLORS = {"WhatsApp":"#4adeaa","SMS":"#2eb88a","Email":"#1d9e75","QR Code":"#0f6e56"}
THEMES = ["Water & Sanitation","Healthcare","Education","Transport","Security","Agriculture"]

PB = dict(paper_bgcolor="rgba(13,51,44,1)",plot_bgcolor="rgba(13,51,44,1)",font=dict(family="DM Sans",color="#e8f5f1"),margin=dict(l=0,r=0,t=36,b=0))

def empty_state(icon, title, sub):
    st.markdown(f"""<div class='empty-state'>
    <div class='empty-state-icon'>{icon}</div>
    <div class='empty-state-title'>{title}</div>
    <div class='empty-state-sub'>{sub}</div>
    </div>""", unsafe_allow_html=True)

def logo_html(size=26):
    return f"""<div style='display:flex;align-items:center;gap:10px;margin-bottom:20px;'>
    <div style='width:{size}px;height:{size}px;background:#4adeaa;border-radius:50%;box-shadow:0 0 10px rgba(74,222,170,0.5);'></div>
    <div><div style='font-size:{size-2}px;font-weight:300;color:#fff;letter-spacing:-0.5px;'>simu</div>
    <div style='font-size:10px;color:rgba(74,222,170,0.6);letter-spacing:0.5px;'>by Sakaza Afrika</div></div></div>"""

def step_bar(current, total=3):
    pips = ""
    for i in range(1, total+1):
        if i == current: cls = "step-pip active"
        elif i < current: cls = "step-pip done"
        else: cls = "step-pip"
        pips += f"<div class='{cls}'></div>"
    return f"<div class='step-bar'>{pips}</div><div style='font-size:11px;color:rgba(232,245,241,0.4);margin-bottom:20px;'>Step {current} of {total}</div>"

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
                if not new_password or not confirm_password: st.error("Please fill in both fields.")
                elif len(new_password) < 8: st.error("Password must be at least 8 characters.")
                elif new_password != confirm_password: st.error("Passwords do not match.")
                else:
                    try:
                        token = st.session_state.get("reset_token")
                        with httpx.Client() as client:
                            r = client.put(f"{SUPABASE_URL}/auth/v1/user", headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json={"password": new_password})
                        if r.status_code == 200:
                            st.success("Password updated! You can now log in.")
                            st.session_state.auth_page = "login"; st.rerun()
                        else: st.error("Something went wrong. Please try again.")
                    except Exception as e: st.error(f"Error: {e}")

def show_landing():
    _,col,_ = st.columns([1,2,1])
    with col:
        st.markdown("<br><br>",unsafe_allow_html=True)
        st.markdown(logo_html(48),unsafe_allow_html=True)
        st.markdown("""<div style='font-family:"DM Serif Display",serif;font-size:44px;font-weight:400;color:#fff;line-height:1.15;letter-spacing:-1px;margin-bottom:16px;'>Every voice<br>has a channel.</div>
        <div style='font-size:16px;color:rgba(232,245,241,0.55);line-height:1.6;margin-bottom:36px;'>Collect authentic community voices at scale — via WhatsApp, SMS, email or QR code. Verified. Structured. Ready to use.</div>""",unsafe_allow_html=True)
        b1,b2 = st.columns(2)
        with b1:
            if st.button("Get started free",use_container_width=True): st.session_state.auth_page="signup"; st.rerun()
        with b2:
            if st.button("Log in",use_container_width=True): st.session_state.auth_page="login"; st.rerun()
        st.markdown("<br>",unsafe_allow_html=True)
        st.markdown("""<div style='display:flex;gap:32px;flex-wrap:wrap;'>
        <div><div style='font-size:20px;font-weight:500;color:#4adeaa;'>20 to 200k</div><div style='font-size:11px;color:rgba(232,245,241,0.4);'>responses at any scale</div></div>
        <div><div style='font-size:20px;font-weight:500;color:#4adeaa;'>4 channels</div><div style='font-size:11px;color:rgba(232,245,241,0.4);'>WhatsApp, SMS, Email, QR</div></div>
        <div><div style='font-size:20px;font-weight:500;color:#4adeaa;'>99%</div><div style='font-size:11px;color:rgba(232,245,241,0.4);'>verified submissions</div></div>
        </div>""",unsafe_allow_html=True)

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
        if st.button("Log in instead",use_container_width=True): st.session_state.auth_page="login"; st.rerun()

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
                                client.post(f"{SUPABASE_URL}/auth/v1/recover", headers={"apikey": SUPABASE_KEY, "Content-Type": "application/json"}, json={"email": reset_email})
                            st.success(f"Password reset link sent to {reset_email} — check your inbox.")
                        except: st.success(f"If that email exists, a reset link has been sent.")
        st.markdown("<div style='text-align:center;margin-top:16px;font-size:13px;color:rgba(232,245,241,0.4);'>Don't have an account?</div>",unsafe_allow_html=True)
        if st.button("Sign up free",use_container_width=True): st.session_state.auth_page="signup"; st.rerun()

def show_create_campaign():
    _,col,_ = st.columns([1,2,1])
    with col:
        st.markdown("<br>",unsafe_allow_html=True)
        st.markdown(logo_html(24),unsafe_allow_html=True)
        st.markdown(st.session_state.campaign_step and step_bar(st.session_state.campaign_step),unsafe_allow_html=True)
        draft = st.session_state.campaign_draft

        if st.session_state.campaign_step == 1:
            st.markdown("<div style='font-size:22px;font-weight:500;color:#fff;margin-bottom:4px;'>Campaign basics</div><div style='font-size:13px;color:rgba(232,245,241,0.4);margin-bottom:20px;'>Name your campaign and tell us who it's for.</div>",unsafe_allow_html=True)
            with st.form("step1_form"):
                campaign_name = st.text_input("Campaign name *", value=draft.get("name",""), placeholder="e.g. Community Water Access Survey")
                org = st.text_input("Organisation *", value=draft.get("organisation", st.session_state.get("user_org","")), placeholder="e.g. ActionAid Kenya")
                description = st.text_area("What is this campaign about? *", value=draft.get("description",""), placeholder="Tell respondents why their voice matters.", height=90)
                col_a,col_b = st.columns(2)
                with col_a: campaign_type = st.selectbox("Campaign type", ["Community reporting","Audience callout","Qualitative research","Campaign storytelling","Needs assessment"])
                with col_b: target = st.selectbox("Target responses", ["20 - 200","200 - 2,000","2,000 - 20,000","20,000+"])
                st.markdown("<br>",unsafe_allow_html=True)
                next1 = st.form_submit_button("Next: Channels", use_container_width=True)
                if next1:
                    if not campaign_name or not org or not description: st.error("Please fill in all required fields.")
                    else:
                        st.session_state.campaign_draft.update({"name":campaign_name,"organisation":org,"description":description,"campaign_type":campaign_type,"target_responses":target})
                        st.session_state.campaign_step = 2; st.rerun()

        elif st.session_state.campaign_step == 2:
            st.markdown("<div style='font-size:22px;font-weight:500;color:#fff;margin-bottom:4px;'>Channels and formats</div><div style='font-size:13px;color:rgba(232,245,241,0.4);margin-bottom:20px;'>How will people reach simu?</div>",unsafe_allow_html=True)
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
                with back2: back_btn = st.form_submit_button("Back", use_container_width=True)
                with next2: next_btn = st.form_submit_button("Next: Story prompts", use_container_width=True)
                if back_btn: st.session_state.campaign_step = 1; st.rerun()
                if next_btn:
                    channels = [c for c,v in [("WhatsApp",ch_wa),("SMS",ch_sms),("Email",ch_email),("QR Code",ch_qr)] if v]
                    formats = [f for f,v in [("Text",fmt_text),("Voice note",fmt_voice),("Photo",fmt_photo)] if v]
                    if not channels: st.error("Please select at least one channel.")
                    else:
                        st.session_state.campaign_draft.update({"channels":channels,"formats":formats,"language":language,"location_tagging":loc_tag})
                        st.session_state.campaign_step = 3; st.rerun()

        elif st.session_state.campaign_step == 3:
            st.markdown("<div style='font-size:22px;font-weight:500;color:#fff;margin-bottom:4px;'>Story prompts</div><div style='font-size:13px;color:rgba(232,245,241,0.4);margin-bottom:20px;'>What do you want to ask respondents?</div>",unsafe_allow_html=True)

            if "prompts_list" not in st.session_state:
                st.session_state.prompts_list = draft.get("prompts", [
                    "Tell us what's happening in your community. What's the biggest challenge you face every day?",
                    "How has this affected you or your family?",
                ])

            to_remove = None
            for i, prompt in enumerate(st.session_state.prompts_list):
                col_p, col_x = st.columns([10,1])
                with col_p:
                    st.markdown(f"""<div class='prompt-block'><div style='font-size:11px;color:rgba(74,222,170,0.6);font-weight:500;margin-bottom:4px;'>Q{i+1}</div><div style='font-size:13px;color:rgba(232,245,241,0.8);'>{prompt}</div></div>""", unsafe_allow_html=True)
                with col_x:
                    if st.button("x", key=f"remove_{i}"): to_remove = i

            if to_remove is not None: st.session_state.prompts_list.pop(to_remove); st.rerun()

            st.markdown("<br>",unsafe_allow_html=True)
            with st.form("add_prompt_form"):
                new_prompt = st.text_input("Add a story prompt", placeholder="e.g. Where are you located?", label_visibility="visible")
                add_btn = st.form_submit_button("Add prompt", use_container_width=True)
                if add_btn and new_prompt.strip(): st.session_state.prompts_list.append(new_prompt.strip()); st.rerun()

            st.markdown("<br>",unsafe_allow_html=True)
            st.markdown('<div style="font-size:12px;font-weight:500;color:rgba(74,222,170,0.8);letter-spacing:0.8px;text-transform:uppercase;margin-bottom:6px;">Closing message</div>', unsafe_allow_html=True)
            closing = st.text_area("", value=draft.get("closing_message","Thank you - your voice will shape real decisions for your community."), height=70, placeholder="Thank respondents and tell them what happens next.", label_visibility="collapsed")
            st.markdown("---",unsafe_allow_html=True)

            back3, launch = st.columns(2)
            with back3:
                if st.button("Back", use_container_width=True): st.session_state.campaign_step = 2; st.rerun()
            with launch:
                if st.button("Go live now", use_container_width=True):
                    if not st.session_state.prompts_list: st.error("Please add at least one story prompt.")
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

def show_launch_confirmation():
    campaign = st.session_state.current_campaign or {}
    name = campaign.get("name","Your campaign")
    slug = campaign.get("slug","your-campaign")
    live_link = f"{RESPOND_BASE}?c={slug}"

    _,col,_ = st.columns([1,2,1])
    with col:
        st.markdown("<br><br>",unsafe_allow_html=True)
        st.markdown(f"""
        <div style='text-align:center;margin-bottom:32px;'>
            <div style='width:72px;height:72px;background:#4adeaa;border-radius:50%;box-shadow:0 0 0 16px rgba(74,222,170,0.1);margin:0 auto 24px;display:flex;align-items:center;justify-content:center;font-size:32px;'>&#10003;</div>
            <div style='font-size:34px;color:#fff;margin-bottom:8px;letter-spacing:-0.5px;'>Your campaign is live.</div>
            <div style='font-size:14px;color:rgba(232,245,241,0.5);'>{name} is ready to receive voices.</div>
        </div>
        """,unsafe_allow_html=True)
        st.markdown("""<div style='background:#0d332c;border:1px solid rgba(74,222,170,0.2);border-radius:10px;padding:20px;margin-bottom:16px;'>
        <div style='font-size:10px;letter-spacing:1px;text-transform:uppercase;color:rgba(74,222,170,0.5);margin-bottom:10px;'>Your campaign link — share this with respondents</div>""",unsafe_allow_html=True)
        st.code(live_link, language=None)
        st.markdown("""<div style='font-size:12px;color:rgba(232,245,241,0.35);margin-top:6px;'>Share via WhatsApp, SMS, email, or print as a QR code.</div></div>""",unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)
        if st.button("Open dashboard", use_container_width=True): st.session_state.show_launch = False; st.rerun()

def show_dashboard():
    campaigns=[]
    try:
        campaigns=supabase_request("GET",f"campaigns?user_id=eq.{st.session_state.user.id}&order=created_at.desc",token=st.session_state.access_token)
        if not isinstance(campaigns,list): campaigns=[]
    except: campaigns=[]

    campaign_name=""; campaign_org=""
    if campaigns:
        campaign_name=campaigns[0].get("name",""); campaign_org=campaigns[0].get("organisation","")
    elif st.session_state.current_campaign:
        campaign_name=st.session_state.current_campaign.get("name",""); campaign_org=st.session_state.current_campaign.get("organisation","")

    real_responses=[]; has_real_data = False
    if campaigns:
        try:
            cid = campaigns[0].get("id")
            real_responses = supabase_request("GET", f"responses?campaign_id=eq.{cid}&order=submitted_at.desc", token=st.session_state.access_token)
            if isinstance(real_responses, list) and len(real_responses) > 0: has_real_data = True
        except: pass

    if has_real_data:
        df = pd.DataFrame(real_responses)
        df = df.rename(columns={"respondent_id":"ID","submitted_at":"Timestamp"})
        if "Timestamp" in df.columns: df["Timestamp"] = pd.to_datetime(df["Timestamp"])
        if "verified" in df.columns: df = df.rename(columns={"verified":"Verified"})
    else:
        df = pd.DataFrame(columns=["ID","Location","Lat","Lon","Channel","Theme","Timestamp","Verified","Format"])

    with st.sidebar:
        st.markdown(logo_html(24),unsafe_allow_html=True)
        st.markdown('<div class="section-label">Navigation</div>',unsafe_allow_html=True)
        page=st.radio("",["Overview","Responses","Voices","Map","Analytics","Reporting"],label_visibility="collapsed")
        st.markdown("---")
        if campaign_name:
            slug = campaigns[0].get("slug","") if campaigns else ""
            campaign_link = f"{RESPOND_BASE}?c={slug}" if slug else ""
            st.markdown(f"""<div style='background:rgba(74,222,170,0.08);border:1px solid rgba(74,222,170,0.2);border-radius:8px;padding:12px 14px;margin-bottom:16px;'>
            <div style='font-size:13px;font-weight:500;color:#e8f5f1;margin-bottom:3px;'>{campaign_name}</div>
            <div style='font-size:11px;color:rgba(74,222,170,0.6);'>{campaign_org}</div>
            <div style='margin-top:8px;'><span class='live-dot'></span><span style='font-size:11px;color:#4adeaa;font-weight:500;'>LIVE</span></div>
            {f"<div style='margin-top:8px;font-size:10px;color:rgba(232,245,241,0.4);word-break:break-all;'>{campaign_link}</div>" if campaign_link else ""}
            </div>""",unsafe_allow_html=True)
        st.markdown("---")
        user_email=st.session_state.user.email if st.session_state.user else ""
        st.markdown(f'<div style="font-size:11px;color:rgba(232,245,241,0.35);margin-bottom:8px;">{user_email}</div>',unsafe_allow_html=True)
        if st.button("+ New campaign"): st.session_state.auth_page="create_campaign"; st.session_state.campaign_step=1; st.session_state.campaign_draft={}; st.rerun()
        if st.button("Log out"): st.session_state.user=None; st.session_state.access_token=None; st.session_state.auth_page="landing"; st.rerun()

    if page=="Overview":
        c1,c2=st.columns([3,1])
        with c1:
            st.markdown(f'<div class="section-label">Campaign overview</div>',unsafe_allow_html=True)
            st.markdown(f'<div class="campaign-title">{campaign_name or "Your dashboard"}</div>',unsafe_allow_html=True)
            st.markdown(f'<div class="campaign-meta">{campaign_org}</div>',unsafe_allow_html=True)
        with c2:
            st.markdown("<div style='text-align:right;padding-top:12px;'><span class='live-dot'></span><span style='font-size:13px;color:#4adeaa;font-weight:500;'>LIVE</span></div>",unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)

        m1,m2,m3,m4=st.columns(4)
        m1.metric("Total responses","0" if not has_real_data else f"{len(df):,}")
        m2.metric("Verified","—")
        m3.metric("Locations","—")
        m4.metric("Avg. response time","—")
        st.markdown("<br>",unsafe_allow_html=True)

        if not has_real_data:
            slug = campaigns[0].get("slug","") if campaigns else ""
            link = f"{RESPOND_BASE}?c={slug}" if slug else ""
            empty_state("📡", "Waiting for voices", f"Your campaign is live. Share the link to start collecting responses.{chr(10)}{link}")
        else:
            df_filtered = df.copy()
            if "Timestamp" in df_filtered.columns:
                df_filtered["Date"] = pd.to_datetime(df_filtered["Timestamp"]).dt.date
                daily = df_filtered.groupby("Date").size().reset_index(name="Count")
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=daily["Date"], y=daily["Count"], mode="lines", fill="tozeroy", line=dict(color="#4adeaa", width=2.5), fillcolor="rgba(74,222,170,0.1)"))
                fig.update_layout(title=dict(text="Responses over time", font=dict(size=13, color="rgba(232,245,241,0.6)"), x=0), xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="rgba(74,222,170,0.07)"), height=220, **PB)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        st.markdown("---")
        st.markdown('<div class="section-label">Latest community voices</div>',unsafe_allow_html=True)
        if has_real_data and "content" in df.columns:
            for _,row in df.head(4).iterrows():
                st.markdown(f'<div class="voice-card"><div class="voice-text">"{row.get("content","")}"</div><div class="voice-meta">location {row.get("location","-")} <span class="voice-badge">{row.get("channel","Web link")}</span> Verified</div></div>',unsafe_allow_html=True)
        else:
            empty_state("🎙️", "No voices yet", "Responses will appear here as they come in.")

    elif page=="Responses":
        st.markdown('<div class="section-label">All responses</div>',unsafe_allow_html=True)
        st.markdown(f'<div class="campaign-title">{len(df):,} submissions</div>',unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)
        if not has_real_data:
            empty_state("📋", "No responses yet", "Submissions will appear here once people start responding.")
        else:
            st.dataframe(df.head(200), use_container_width=True, height=480, hide_index=True)
            csv2 = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download CSV", data=csv2, file_name="simu_responses.csv", mime="text/csv")

    elif page=="Voices":
        st.markdown('<div class="section-label">Community voices</div>',unsafe_allow_html=True)
        st.markdown('<div class="campaign-title">Straight from the source.</div>',unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)
        if not has_real_data:
            empty_state("🎙️", "No voices yet", "Real responses will appear here as they come in.")
        else:
            for _,row in df.head(20).iterrows():
                st.markdown(f'<div class="voice-card"><div class="voice-text">"{row.get("content","")}"</div><div class="voice-meta">location {row.get("location","-")} <span class="voice-badge">{row.get("channel","Web link")}</span> Verified</div></div>',unsafe_allow_html=True)

    elif page=="Map":
        st.markdown('<div class="section-label">Response map</div>',unsafe_allow_html=True)
        st.markdown('<div class="campaign-title">Where voices are coming from</div>',unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)
        if not has_real_data:
            empty_state("🗺️", "No location data yet", "Response locations will appear on the map as submissions come in.")
        else:
            if "Lat" in df.columns and "Lon" in df.columns:
                fm = px.scatter_mapbox(df, lat="Lat", lon="Lon", zoom=4, center={"lat": 0.0, "lon": 20.0}, mapbox_style="carto-darkmatter")
                fm.update_traces(marker=dict(size=9, color="#4adeaa", opacity=0.75))
                fm.update_layout(height=520, **PB)
                st.plotly_chart(fm, use_container_width=True, config={"displayModeBar": False})

    elif page=="Analytics":
        st.markdown('<div class="section-label">Analytics</div>',unsafe_allow_html=True)
        st.markdown('<div class="campaign-title">Deep dive</div>',unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)
        if not has_real_data:
            empty_state("📊", "No data yet", "Analytics will populate as responses come in.")
        else:
            st.dataframe(df.describe(), use_container_width=True)

    elif page=="Reporting":
        st.markdown('<div class="section-label">Reporting</div>',unsafe_allow_html=True)
        st.markdown('<div class="campaign-title">Export and share your data</div>',unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)
        if not has_real_data:
            empty_state("📥", "No data to export yet", "Once responses come in you can download them as a CSV.")
        else:
            st.markdown("""<div style='background:#0d332c;border:1px solid rgba(74,222,170,0.15);border-radius:10px;padding:24px;margin-bottom:16px;'>
            <div style='font-size:13px;font-weight:500;color:#4adeaa;margin-bottom:8px;'>CSV Export</div>
            <div style='font-size:13px;color:rgba(232,245,241,0.6);margin-bottom:16px;'>Download all responses as a spreadsheet.</div>
            </div>""",unsafe_allow_html=True)
            csv_all = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download full CSV", data=csv_all, file_name="simu_responses.csv", mime="text/csv", use_container_width=True)

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

if st.session_state.auth_page == "reset_password":
    show_reset_password()
elif st.session_state.user is None:
    if st.session_state.auth_page=="signup": show_signup()
    elif st.session_state.auth_page=="login": show_login()
    else: show_landing()
else:
    if st.session_state.auth_page=="create_campaign": show_create_campaign()
    elif st.session_state.show_launch: show_launch_confirmation()
    else: show_dashboard()
