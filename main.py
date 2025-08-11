# main.py
from story_generator import FACTS  
import os
import csv
import json
import random
import urllib.parse
import streamlit as st
from story_generator import (
    generate_parsverse_myth,
    generate_parsverse_profile,
    REGIONS,
)

# ------------------ Config ------------------
APP_URL = os.getenv("APP_URL", "").strip()  # set in Streamlit Secrets for share links
st.set_page_config(page_title="ParsVerse – Myth & Persona", page_icon="🏛️", layout="centered")

# ------------------ Brand CSS (Persian turquoise + gold) ------------------
BRAND_CSS = """
<style>
:root{
  --bg:#fffdf7;           /* parchment cream */
  --card:#fcf5e6;         /* parchment card */
  --ink:#12222a;          /* deep ink */
  --gold:#c2a14d;         /* Persian gold */
  --turq:#1f8a8a;         /* Persian turquoise */
  --turq-deep:#0f6d6d;
}
html, body, [data-testid="stAppViewContainer"]{ background:var(--bg); color:var(--ink); }
.block-container{ padding-top:2rem; }

/* Header */
.brand-wrap{ display:flex; align-items:center; justify-content:center; gap:14px; margin-bottom:6px; }
.brand-title{ font-size:44px; font-weight:800; letter-spacing:.4px; margin:0; color:var(--turq-deep); }
.brand-sub{ text-align:center; margin:6px 0 0 0; color:#213b40; }
.badge{
  display:inline-block; padding:4px 10px; border:1px solid var(--gold);
  border-radius:999px; background:#fff; font-size:12px; margin-left:8px;
}

/* Cards */
.pars-card{
  background:var(--card); padding:22px; border:2px solid var(--gold);
  border-radius:14px; font-family:Georgia,serif; box-shadow:0 8px 24px rgba(0,0,0,0.06);
}
.pars-scroll{
  background:var(--card); padding:18px; border:1px solid #d8caa1;
  border-radius:10px; font-family:Georgia,serif;
}

/* Dividers & links */
.divider{height:1px;background:linear-gradient(90deg, transparent, var(--gold), transparent);margin:18px 0;}
a, .sharebar a{ color:var(--turq-deep); text-decoration:none; }
.sharebar a:hover{ text-decoration:underline; }

/* Buttons */
.copybtn{
  border:1px solid var(--gold); padding:6px 10px; border-radius:8px; background:#fff; cursor:pointer;
}

/* Footer */
.footer{
  margin-top:28px; padding:10px 12px; border-top:1px solid var(--gold);
  text-align:center; color:#32565b; font-size:13px;
}
</style>
"""
st.markdown(BRAND_CSS, unsafe_allow_html=True)

# ------------------ Tiny global counter (file-based) ------------------
COUNTER_FILE = os.path.join(os.path.dirname(__file__), "counter.json")
def _load_counts():
    try:
        with open(COUNTER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"total": 0, "myths": 0, "personas": 0}
def _save_counts(data):
    try:
        with open(COUNTER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass  # ephemeral on Cloud is fine for MVP

GLOBAL_COUNTS = _load_counts()

# Keep counters in session so header updates without rerun
if "counts" not in st.session_state:
    st.session_state.counts = GLOBAL_COUNTS

def bump_counter(kind):
    data = _load_counts()
    data["total"] = data.get("total", 0) + 1
    if kind == "myth":
        data["myths"] = data.get("myths", 0) + 1
    elif kind == "persona":
        data["personas"] = data.get("personas", 0) + 1
    _save_counts(data)
    st.session_state.counts = data  # live update header badge
    return data

# ------------------ Session usage limits ------------------
MYTH_LIMIT = 5
PERSONA_LIMIT = 3

if "quota" not in st.session_state:
    st.session_state.quota = {"myth": 0, "persona": 0}

def can_make(kind: str) -> bool:
    used = st.session_state.quota.get(kind, 0)
    cap = MYTH_LIMIT if kind == "myth" else PERSONA_LIMIT
    return used < cap

def note_usage(kind: str):
    st.session_state.quota[kind] = st.session_state.quota.get(kind, 0) + 1

def remaining(kind: str) -> int:
    used = st.session_state.quota.get(kind, 0)
    cap = MYTH_LIMIT if kind == "myth" else PERSONA_LIMIT
    return max(0, cap - used)

# ------------------ Session history ------------------
if "history" not in st.session_state:
    st.session_state.history = {"myths": [], "personas": []}

# ------------------ Analytics CSV (lightweight) ------------------
LOG_FILE = os.path.join(os.path.dirname(__file__), "analytics.csv")
def log_event(kind, payload: dict):
    try:
        new = {"kind": kind, **payload}
        write_header = not os.path.exists(LOG_FILE)
        with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=new.keys())
            if write_header: w.writeheader()
            w.writerow(new)
    except Exception:
        pass  # fine on ephemeral Cloud

# ------------------ Did you know facts ------------------
FACTS = [
    "“Farr / Farrah (xvarənah)” denotes divine royal glory in Iranian tradition.",
    "Takht-e Jamshid (Parsa/Persepolis) bears inscriptions in Old Persian, Elamite, and Babylonian.",
    "Kourosh (Cyrus) founded Pasargad, the early Achaemenid capital.",
    "Hagmatāna (Hamadan/Ecbatana) was a Median royal center with layered fortifications.",
    "Tisfun (Ctesiphon) served as a grand Sasanian capital on the Tigris.",
    "The Shahnameh preserves epic cycles like Rostam of Sistan/Zabulistan.",
    "Sogdian merchants connected Iran to the Silk Roads via Samarkand and Bukhara.",
    "Hyrcanian forests along the Caspian are among the world’s oldest temperate rainforests.",
    "Parthian cataphracts were famed for heavy armor on both rider and horse.",
]


# ------------------ Header with inline SVG mark ------------------
SVG_LOGO = """
<svg width="42" height="42" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" aria-label="ParsVerse logo">
  <defs>
    <linearGradient id="g" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0%" stop-color="#1f8a8a"/>
      <stop offset="100%" stop-color="#0f6d6d"/>
    </linearGradient>
  </defs>
  <circle cx="32" cy="32" r="30" fill="url(#g)" stroke="#c2a14d" stroke-width="3"/>
  <!-- stylized cypress / column -->
  <path d="M32 12 C28 20, 28 26, 32 30 C36 26, 36 20, 32 12 Z" fill="#fff"/>
  <rect x="30.8" y="30" width="2.4" height="18" fill="#fff"/>
  <circle cx="32" cy="52" r="3" fill="#c2a14d"/>
</svg>
"""

st.markdown(f"""
<div class="brand-wrap">
  {SVG_LOGO}
  <h1 class="brand-title">ParsVerse</h1>
</div>
<p class="brand-sub">
  Create your Persian-inspired <strong>myth</strong> or a <strong>detailed persona</strong> (kingdom, locale, role, backstory).
  <span class="badge">Total legends woven: {st.session_state.counts.get('total', 0)}</span>
</p>
""", unsafe_allow_html=True)
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ------------------ Quick Myth ------------------
with st.expander("✨ Quick Myth (simple scroll)", expanded=True):
    with st.form("quick_myth_form"):
        q_col1, q_col2 = st.columns([1, 1])
        with q_col1:
            q_name = st.text_input("Your name", key="q_name")
        with q_col2:
            q_region = st.selectbox("Historical region", REGIONS, index=0, key="q_region")
        q_style = st.selectbox("Style / tone", ["Epic", "Mystic", "Royal", "Poet"], index=0, key="q_style")
        st.caption(f"Remaining this session: {remaining('myth')} myth generations")
        q_submit = st.form_submit_button("Generate Myth")

    if q_submit:
        if not q_name or not q_region:
            st.warning("Please enter a name and choose a region.")
        elif not can_make("myth"):
            st.error("You’ve reached the session limit for myths. Please come back later!")
        else:
            tip = random.choice(FACTS)
            with st.spinner(f"Weaving your legend… (Did you know? {tip})"):
                myth = generate_parsverse_myth(q_name, q_region, q_style)

            st.success("Your scroll is ready!")
            st.markdown('<div class="pars-card"><h3 style="text-align:center;margin-top:0;">🪶 ParsVerse Scroll</h3></div>', unsafe_allow_html=True)
            st.markdown(f"<div class='pars-scroll'><p style='font-size:18px;line-height:1.7;white-space:pre-wrap;'>{myth}</p></div>", unsafe_allow_html=True)

            if st.button("🔄 Try another wording", key="myth_variant"):
                tip = random.choice(FACTS)
                with st.spinner(f"Refining the scroll… (Did you know? {tip})"):
                    myth2 = generate_parsverse_myth(q_name, q_region, q_style)
                st.markdown(
                    f"<div style='background:#fdf6e3;padding:18px;border:1px solid #d8caa1;border-radius:10px;"
                    f"font-family:Georgia,serif;'><p style='font-size:18px;line-height:1.7;white-space:pre-wrap;'>{myth2}</p></div>",
                    unsafe_allow_html=True
                )

            # Download myth as .txt
            st.download_button(
                label="⬇️ Download Myth (.txt)",
                data=myth.encode("utf-8"),
                file_name=f"parsverse_myth_{q_name or 'anon'}.txt",
                mime="text/plain"
            )

            # Share to X (Twitter) + copy to clipboard
            quoted = urllib.parse.quote_plus(f"My ParsVerse myth ✨ — {APP_URL}" if APP_URL else "My ParsVerse myth ✨")
            tw_url = f"https://twitter.com/intent/tweet?text={quoted}"
            st.markdown(f"<div class='sharebar' style='margin-top:8px;'><a href='{tw_url}' target='_blank'>🐦 Share on X</a></div>", unsafe_allow_html=True)
            st.markdown("""
            <button class="copybtn" onclick="navigator.clipboard.writeText(document.getElementById('mythtext').innerText)">Copy myth to clipboard</button>
            <pre id="mythtext" style="position:absolute;left:-9999px;white-space:pre-wrap;">{}</pre>
            """.format(myth.replace("<","&lt;").replace(">","&gt;")), unsafe_allow_html=True)

            # History + counters + quota
            st.session_state.history["myths"].append({
                "name": q_name, "region": q_region, "style": q_style, "text": myth
            })
            note_usage("myth")
            bump_counter("myth")
            log_event("myth", {"name": q_name, "region": q_region, "style": q_style})

            st.button("🔁 Generate another myth", key="regen_myth")

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ------------------ Detailed Persona ------------------
st.markdown("## 🔎 Detailed Persona (kingdom, locale, role + backstory)")

with st.form("detail_persona_form"):
    d_col1, d_col2 = st.columns(2)
    with d_col1:
        d_name = st.text_input("Your name", key="d_name")
        d_region = st.selectbox("Historical region", REGIONS, index=0, key="d_region")
        d_age = st.number_input("Age", min_value=12, max_value=90, value=24, step=1, key="d_age")
    with d_col2:
        d_gender = st.selectbox("Gender", ["Female", "Male", "Non-binary", "Prefer not to say"], key="d_gender")
        d_style = st.selectbox("Style / tone", ["Epic", "Mystic", "Royal", "Poet"], index=0, key="d_style")
        d_hobby = st.text_input("Hobby / Work (e.g., scholar, archer, merchant, healer)", key="d_hobby")

    d_traits = st.multiselect(
        "Core traits (pick 1–4)",
        ["brave", "wise", "just", "mercurial", "stoic", "devout", "curious", "cunning", "compassionate", "ambitious"],
        default=["brave", "curious"],
        key="d_traits"
    )
    st.caption(f"Remaining this session: {remaining('persona')} persona generations")
    d_submit = st.form_submit_button("Generate Detailed Persona")

if d_submit:
    if not d_name or not d_region:
        st.warning("Please enter a name and choose a region.")
    elif not can_make("persona"):
        st.error("You’ve reached the session limit for personas. Please come back later!")
    else:
        tip = random.choice(FACTS)
        with st.spinner(f"Consulting the court archives… (Did you know? {tip})"):
            profile = generate_parsverse_profile(
                name=d_name,
                region=d_region,
                age=int(d_age),
                gender=d_gender,
                traits=d_traits,
                hobby=d_hobby or "general civic duties",
                style=d_style
            )

        st.success("Your persona is ready!")
        st.markdown('<div class="pars-card"><h3 style="text-align:center;margin-top:0;">👑 Persona Dossier</h3></div>', unsafe_allow_html=True)

        role = profile.get("role", "") or "Citizen"
        locale = profile.get("locale", "") or d_region
        titles = profile.get("titles", []) or []
        st.markdown(
            f"<h4 style='text-align:center;margin:8px 0 2px 0;'>{role} of {locale}</h4>"
            f"<p style='text-align:center;margin-top:0;'><em>{', '.join(titles)}</em></p>",
            unsafe_allow_html=True
        )

        st.markdown(f"<div class='pars-scroll'><p style='font-size:18px;line-height:1.7;white-space:pre-wrap;'>{profile.get('backstory','')}</p></div>", unsafe_allow_html=True)

        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"**Kingdom:**<br>{profile.get('kingdom','')}", unsafe_allow_html=True)
            st.markdown(f"**Locale:**<br>{profile.get('locale','')}", unsafe_allow_html=True)
        with c2:
            st.markdown(f"**Role:**<br>{profile.get('role','')}", unsafe_allow_html=True)
            st.markdown(f"**Symbols:**<br>{', '.join(profile.get('symbols', []))}", unsafe_allow_html=True)
        with c3:
            st.markdown(f"**Artifact:**<br>{profile.get('artifact','')}", unsafe_allow_html=True)
            st.markdown(f"**Motto:**<br><em>{profile.get('motto','')}</em>", unsafe_allow_html=True)

        if st.button("🔄 Try another persona", key="persona_variant"):
            tip = random.choice(FACTS)
            with st.spinner(f"Reimagining your station… (Did you know? {tip})"):
                profile2 = generate_parsverse_profile(
                    name=d_name, region=d_region, age=int(d_age),
                    gender=d_gender, traits=d_traits,
                    hobby=d_hobby or "general civic duties",
                    style=d_style
                )
            st.markdown("#### Alternate persona")
            st.markdown(
                f"<div style='background:#fdf6e3;padding:18px;border:1px solid #d8caa1;border-radius:10px;"
                f"font-family:Georgia,serif;'><p style='font-size:17px;line-height:1.7;white-space:pre-wrap;'>{profile2.get('backstory','')}</p></div>",
                unsafe_allow_html=True
            )

        # Quick facts (add under the existing columns)
        st.markdown("---")
        st.markdown(f"**Favorite food:** {profile.get('favorite_food','')}")
        st.markdown(f"**Hobby:** {profile.get('hobby','')}")
        st.markdown(f"**Friends:** {profile.get('friends','')}")

        # Short story block (more readable)
        st.markdown("### Short story")
        st.markdown(
            f"<div class='pars-scroll'><p style='font-size:17px;line-height:1.7;white-space:pre-wrap;'>{profile.get('short_story','')}</p></div>",
            unsafe_allow_html=True
        )


        # Downloads
        persona_json_str = json.dumps(profile, ensure_ascii=False, indent=2)
        st.markdown("---")
        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            st.download_button(
                label="⬇️ Download Persona JSON",
                data=persona_json_str.encode("utf-8"),
                file_name=f"parsverse_persona_{d_name or 'anon'}.json",
                mime="application/json"
            )
        with dl_col2:
            persona_txt = f"""ParsVerse Persona
Name: {d_name}
Kingdom: {profile.get('kingdom','')}
Locale: {profile.get('locale','')}
Role: {profile.get('role','')}
Titles: {', '.join(profile.get('titles', []))}
Symbols: {', '.join(profile.get('symbols', []))}
Artifact: {profile.get('artifact','')}
Motto: {profile.get('motto','')}

Backstory:
{profile.get('backstory','')}
"""
            st.download_button(
                label="⬇️ Download Persona (.txt)",
                data=persona_txt.encode("utf-8"),
                file_name=f"parsverse_persona_{d_name or 'anon'}.txt",
                mime="text/plain"
            )

        # Share
        share_text = f"My ParsVerse persona: {role} of {locale} — {APP_URL}" if APP_URL else f"My ParsVerse persona: {role} of {locale}"
        tw_url = f"https://twitter.com/intent/tweet?text={urllib.parse.quote_plus(share_text)}"
        st.markdown(f"<div class='sharebar' style='margin-top:8px;'><a href='{tw_url}' target='_blank'>🐦 Share on X</a></div>", unsafe_allow_html=True)

        # History + counters + quota + analytics
        st.session_state.history["personas"].append({
            "name": d_name, "region": d_region, "age": int(d_age),
            "gender": d_gender, "traits": d_traits, "hobby": d_hobby,
            "profile": profile
        })
        note_usage("persona")
        bump_counter("persona")
        log_event("persona", {"name": d_name, "region": d_region, "age": int(d_age), "role": profile.get("role","")})

        st.button("🔁 Generate another persona", key="regen_persona")

# ------------------ Session History ------------------
with st.expander("🗂️ Your session history"):
    if st.session_state.history["myths"]:
        st.markdown("**Myths (last 5)**")
        for i, m in enumerate(reversed(st.session_state.history["myths"][-5:]), 1):
            st.markdown(f"{i}. *{m['name']}* — {m['region']} / {m['style']}")
            st.code(m["text"])
    if st.session_state.history["personas"]:
        st.markdown("**Personas (last 5)**")
        for i, p in enumerate(reversed(st.session_state.history["personas"][-5:]), 1):
            meta = p["profile"]
            st.markdown(f"{i}. *{p['name']}* — {meta.get('role','')} of {meta.get('locale','')}")
            st.code(meta.get("backstory",""))

# ------------------ About ------------------
with st.expander("ℹ️ About ParsVerse"):
    st.markdown("""
ParsVerse crafts Iranian-inspired myths and personas. We prefer **Iranian endonyms** and sanitize non-Iranian terms.
Results are generated by AI with strict prompt constraints — treat them as creative storytelling, not academic citations.
""")

# ------------------ Footer ------------------
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown("<div class='footer'>Crafted with 🪶 in turquoise & gold • ParsVerse</div>", unsafe_allow_html=True)
