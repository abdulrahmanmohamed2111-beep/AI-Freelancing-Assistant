"""Presentation only: styles and escaped display components."""
from html import escape

import streamlit as st


def styles():
    st.markdown('''<style>
    .stApp {background:#f5f7fa;color:#172b43}
    .block-container {max-width:1220px;padding-top:2.5rem;padding-bottom:3rem}
    h1,h2,h3 {letter-spacing:-.035em;color:#172b43}
    h1 {font-size:2.65rem!important;line-height:1.15!important;font-weight:750!important}
    h3 {font-size:1.18rem!important}
    [data-testid="stHeader"] {background:rgba(245,247,250,.95)}
    [data-testid="stSidebar"] {background:#fff;border-right:1px solid #e2e8f0}
    [data-testid="stSidebar"] .block-container {padding-top:2rem}
    [data-testid="stSidebar"] hr {margin:1.4rem 0}
    [data-testid="stVerticalBlockBorderWrapper"] > div {border-radius:16px}
    [data-testid="stTextArea"] textarea {background:#f8fafc;color:#172b43!important;
      border-radius:10px;line-height:1.75;font-size:15px}
    [data-testid="stTextArea"] textarea:disabled {-webkit-text-fill-color:#44566c;opacity:1}
    [data-testid="stButton"] button,[data-testid="stDownloadButton"] button {
      border-radius:10px;min-height:45px;font-weight:600;transition:background .15s}
    [data-testid="stBaseButton-primary"] {background:#087f73;border:1px solid #087f73;color:white}
    [data-testid="stBaseButton-primary"]:hover {background:#06665d;border-color:#06665d;color:white}
    button:focus-visible,textarea:focus-visible {outline:3px solid #30b4a2!important;outline-offset:3px}
    [data-testid="stMetric"] {background:#fff;border:1px solid #e1e8ef;border-radius:14px;padding:18px 20px}
    [data-testid="stMetricValue"] {font-size:1.65rem;font-weight:700}
    [data-baseweb="tab-list"] {gap:22px;border-bottom:1px solid #dfe6ed}
    [data-baseweb="tab"] {padding:12px 0;font-weight:600}
    .brand {display:flex;gap:10px;align-items:center;font-weight:750;font-size:21px;margin:8px 0 30px}
    .brand-icon {background:#087f73;color:white;width:37px;height:37px;display:grid;place-items:center;border-radius:11px;font-size:22px}
    .eyebrow {font-size:11px;font-weight:750;letter-spacing:.14em;color:#66788c;margin:18px 0 12px;text-transform:uppercase}
    .nav-active {background:#e8f5f2;color:#086b60;border-radius:9px;padding:12px 14px;font-size:14px;font-weight:650}
    .roadmap {padding:10px 14px;color:#65768b;font-size:13px;display:flex;justify-content:space-between;gap:10px}
    .roadmap small {color:#65768b;font-size:10px;border:1px solid #e0e6ec;border-radius:5px;padding:1px 5px}
    .workspace {border-top:1px solid #e4eaf0;margin-top:34px;padding-top:20px;font-size:13px;color:#61748a}
    .workspace strong {color:#223b51;display:block;margin-bottom:4px}
    .topline {display:flex;align-items:center;justify-content:space-between;gap:12px;margin:10px 0 28px;color:#64768a;font-size:12px}
    .pill {display:inline-block;background:#e6f3f0;border:1px solid #c9e6df;color:#08685e;border-radius:30px;padding:5px 11px;font-size:11px;font-weight:650}
    .intro {max-width:650px;color:#607187;font-size:16px;line-height:1.7;margin:0 0 22px}
    .steps {display:flex;gap:10px;align-items:center;color:#6c7c8f;font-size:12px;margin:4px 0 28px;flex-wrap:wrap}
    .steps strong {color:#087f73}.steps span {color:#b3bdc8}
    .demo-note {border-left:3px solid #d5a54a;background:#fff8e9;padding:12px 15px;border-radius:7px;color:#775b21;font-size:13px;line-height:1.6;margin-bottom:20px}
    .guide {background:#eaf2f5;border:1px solid #dae6ec;border-radius:16px;padding:25px;margin-top:0}
    .guide h3 {margin:0 0 10px;font-size:19px!important}.guide p {font-size:13px;color:#52697c;line-height:1.7}
    .guide-item {display:flex;gap:12px;margin-top:22px;font-size:13px;line-height:1.6}
    .guide-num {flex-shrink:0;width:26px;height:26px;border:1px solid #cbdde3;border-radius:8px;text-align:center;color:#087267;font-weight:700}
    .guide-item strong {display:block;color:#233d51}.guide-item div {color:#587083}
    .empty {padding:36px 24px;text-align:center;border:1px dashed #cbd7e2;border-radius:16px;background:#f9fbfc;margin-top:16px}
    .empty-icon {margin:auto auto 12px;border-radius:12px;background:#e8f2f1;width:44px;height:44px;display:grid;place-items:center;color:#087f73;font-size:24px}
    .empty strong {font-size:16px}.empty p {color:#6a7e91;font-size:13px;margin:8px 0 0}
    .evidence {border:1px solid #e0e7ee;background:white;border-radius:12px;padding:18px 20px;margin:12px 0}
    .evidence-title {font-weight:650;color:#20374d;line-height:1.6;font-size:15px;overflow-wrap:anywhere}
    .source {border-left:2px solid #b7dcd4;padding-left:12px;margin-top:12px;color:#5a7182;font-size:13px;line-height:1.6;overflow-wrap:anywhere}
    .source small {display:block;color:#527067;font-size:10px;letter-spacing:.08em;margin-bottom:4px}
    .footer {color:#6b7c8f;font-size:11px;margin-top:30px;padding-top:17px;border-top:1px solid #dfe6ed}
    @media(max-width:700px){.block-container{padding:1.5rem 1rem}h1{font-size:2rem!important}.topline{margin-bottom:20px}.guide{padding:20px}.steps{gap:7px}}
    </style>''', unsafe_allow_html=True)


def evidence_card(description, quote):
    st.markdown(f'<div class="evidence"><div class="evidence-title">{escape(description)}</div>'
                f'<div class="source"><small>SOURCE EVIDENCE</small>“{escape(quote)}”</div></div>',
                unsafe_allow_html=True)
