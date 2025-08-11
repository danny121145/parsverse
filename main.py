# main.py
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

/* Decorated illuminated card */
.illum-card{
  --gold:#c2a14d; --turq:#1f8a8a; --turq-deep:#0f6d6d; --paper:#fffaf0; --ink:#102126;
  background:
    radial-gradient(ellipse at top left, rgba(194,161,77,.10), transparent 60%),
    radial-gradient(ellipse at bottom right, rgba(31,138,138,.08), transparent 60%),
    repeating-linear-gradient(45deg, rgba(194,161,77,.06) 0 10px, transparent 10px 20px),
    var(--paper);
  border: 4px solid var(--gold);
  border-radius: 18px;
  box-shadow: 0 12px 30px rgba(0,0,0,.12);
  padding: 18px 18px 16px;
  color: var(--ink);
  position: relative;
  overflow: hidden;
}
.illum-header{
  display:flex; flex-direction:column; align-items:center; gap:4px; margin-bottom:8px;
}
.illum-title{
  font-weight:800; font-size:24px; color:var(--turq-deep); letter-spacing:.3px; margin:4px 0 0;
}
.illum-sub{
  font-style:italic; color:#23444a; margin:0;
}
.illum-divider{
  height:10px; margin:10px 0 14px;
  background:
    conic-gradient(from 0deg, #fff 0 25%, rgba(0,0,0,0) 0 100%) 0 0/16px 10px repeat-x,
    linear-gradient(90deg, transparent, var(--gold), transparent);
}
.illum-grid{
  display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:8px 16px;
}
.illum-label{ font-weight:700; color:#2a4e54; }
.illum-scroll{
  background: rgba(255,255,255,.65);
  border: 1px solid rgba(194,161,77,.45);
  border-radius: 12px;
  padding: 12px 14px;
  font-family: Georgia, serif;
  line-height: 1.7;
}
.chips{ display:flex; flex-wrap:wrap; gap:6px; margin:2px 0 0; }
.chip{
  border:1px solid rgba(194,161,77,.55);
  padding:3px 8px; border-radius:999px; background:#fff; font-size:12px;
}
.illum-ornament{
  position:absolute; inset:auto -40px -40px auto; width:160px; height:160px;
  background: radial-gradient(circle at 30% 30%, rgba(194,161,77,.25), rgba(194,161,77,0) 60%),
              radial-gradient(circle at 70% 70%, rgba(31,138,138,.18), rgba(31,138,138,0) 60%);
  filter: blur(1px);
  pointer-events:none;
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

# --------- Formatters for illuminated cards ----------
def format_persona_persian(data: dict, *, name: str | None = None) -> str:
    titles = ", ".join(data.get("titles", [])) or ""
    symbols = data.get("symbols", [])
    role = data.get("role","")
    locale = data.get("locale","")
    kingdom = data.get("kingdom","")
    motto = data.get("motto","")

    header_line = f"{role} of {locale}" if role or locale else kingdom
    display_name = name or titles or ""
    subtitle = motto

    chips_html = "".join([f"<span class='chip'>{s}</span>" for s in symbols])

    return f"""
<div class="illum-card">
  <div class="illum-ornament"></div>
  <div class="illum-header">
    <div class="illum-title">{header_line}</div>
    {'<p class="illum-sub">'+subtitle+'</p>' if subtitle else ''}
    {'<p class="illum-sub">'+display_name+'</p>' if display_name else ''}
  </div>

  <div class="illum-divider"></div>

  <div class="illum-grid">
    <div><span class="illum-label">Kingdom:</span><br>{kingdom}</div>
    <div><span class="illum-label">Locale:</span><br>{locale}</div>
    <div><span class="illum-label">Role:</span><br>{role}</div>
    <div><span class="illum-label">Favorite food:</span><br>{data.get('favorite_food','')}</div>
    <div><span class="illum-label">Hobby:</span><br>{data.get('hobby','')}</div>
    <div><span class="illum-label">Friends:</span><br>{data.get('friends','')}</div>
    <div><span class="illum-label">Artifact:</span><br>{data.get('artifact','')}</div>
    <div><span class="illum-label">Symbols:</span><br><div class="chips">{chips_html}</div></div>
  </div>

  <div class="illum-divider"></div>

  <div class="illum-grid">
    <div>
      <div class="illum-label" style="margin-bottom:4px;">Appearance</div>
      <div class="illum-scroll">{data.get('appearance','')}</div>
    </div>
    <div>
      <div class="illum-label" style="margin-bottom:4px;">Dwelling</div>
      <div class="illum-scroll">{data.get('dwelling','')}</div>
    </div>
  </div>

  <div style="height:12px;"></div>

  <div>
    <div class="illum-label" style="margin-bottom:4px;">Daily routine</div>
    <div class="illum-scroll">{data.get('daily_routine','')}</div>
  </div>

  <div style="height:12px;"></div>

  <div>
    <div class="illum-label" style="margin-bottom:4px;">Festival</div>
    <div class="illum-scroll">{data.get('festival','')}</div>
  </div>

  <div class="illum-divider"></div>

  <div>
    <div class="illum-label" style="margin-bottom:4px;">Short story</div>
    <div class="illum-scroll">{data.get('short_story','')}</div>
  </div>

  <div style="height:12px;"></div>

  <div>
    <div class="illum-label" style="margin-bottom:4px;">Backstory</div>
    <div class="illum-scroll">{data.get('backstory','')}</div>
  </div>
</div>
""".strip()

def format_myth_persian(myth_text: str, *, name: str = "", region: str = "", style: str = "") -> str:
    header_line = f"Scroll of {name}" if name else "ParsVerse Scroll"
    chips_html = "".join([f"<span class='chip'>{c}</span>" for c in [region, style] if c])
    return f"""
<div class="illum-card">
  <div class="illum-ornament"></div>
  <div class="illum-header">
    <div class="illum-title">{header_line}</div>
    {'<p class="illum-sub">'+region+'</p>' if region else ''}
  </div>

  <div class="illum-divider"></div>

  <div class="illum-grid">
    <div><span class="illum-label">Region:</span><br>{region or '-'}</div>
    <div><span class="illum-label">Tone:</span><br>{style or '-'}</div>
    <div><span class="illum-label">Badges:</span><br><div class="chips">{chips_html}</div></div>
  </div>

  <div class="illum-divider"></div>

  <div>
    <div class="illum-label" style="margin-bottom:4px;">Myth</div>
    <div class="illum-scroll" id="myth-text">{myth_text}</div>
  </div>
</div>
""".strip()

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

        # NEW: depth knobs
        q_detail = st.slider("Detail level", 1, 3, 2, help="1=short, 2=medium, 3=rich")
        q_strict = st.slider("Historical strictness", 0.0, 1.0, 0.6, 0.1, help="Higher = more historically grounded, less mythic fluff")
        q_themes = st.text_input("Themes (comma separated, optional)", help="e.g., loyalty, water, journey")

        st.caption(f"Remaining this session: {remaining('myth')} myth generations")
        q_submit = st.form_submit_button("Generate Myth")

    if q_submit:
        if not q_name or not q_region:
            st.warning("Please enter a name and choose a region.")
        elif not can_make("myth"):
            st.error("You’ve reached the session limit for myths. Please come back later!")
        else:
            tip = random.choice(FACTS)
            themes_list = [t.strip() for t in (q_themes or "").split(",") if t.strip()]
            with st.spinner(f"Weaving your legend… (Did you know? {tip})"):
                myth = generate_parsverse_myth(
                    q_name, q_region, q_style,
                    detail_level=q_detail, strictness=q_strict, themes=themes_list
                )

            st.success("Your scroll is ready!")
            st.markdown(
                format_myth_persian(myth, name=q_name, region=q_region, style=q_style),
                unsafe_allow_html=True
            )

            # Try another wording (uses the same knobs)
            if st.button("🔄 Try another wording", key="myth_variant"):
                tip = random.choice(FACTS)
                with st.spinner(f"Refining the scroll… (Did you know? {tip})"):
                    myth2 = generate_parsverse_myth(
                        q_name, q_region, q_style,
                        detail_level=q_detail, strictness=q_strict, themes=themes_list
                    )
                st.markdown(
                    format_myth_persian(myth2, name=q_name, region=q_region, style=q_style),
                    unsafe_allow_html=True
                )

            # Download myth as .txt
            st.download_button(
                label="⬇️ Download Myth (.txt)",
                data=myth.encode("utf-8"),
                file_name=f"parsverse_myth_{q_name or 'anon'}.txt",
                mime="text/plain"
            )

            # Copy button for illuminated myth card
            st.markdown("""
            <button class="copybtn" onclick="navigator.clipboard.writeText(document.getElementById('myth-text').innerText)">
                Copy myth to clipboard
            </button>
            """, unsafe_allow_html=True)

            # Share to X (Twitter)
            quoted = urllib.parse.quote_plus(f"My ParsVerse myth ✨ — {APP_URL}" if APP_URL else "My ParsVerse myth ✨")
            tw_url = f"https://twitter.com/intent/tweet?text={quoted}"
            st.markdown(f"<div class='sharebar' style='margin-top:8px;'><a href='{tw_url}' target='_blank'>🐦 Share on X</a></div>", unsafe_allow_html=True)

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
                style=d_style,
                detail_level=2
            )

        st.success("Your persona is ready!")
        st.markdown(format_persona_persian(profile, name=d_name), unsafe_allow_html=True)

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

Appearance:
{profile.get('appearance','')}

Dwelling:
{profile.get('dwelling','')}

Daily routine:
{profile.get('daily_routine','')}

Festival:
{profile.get('festival','')}

Short story:
{profile.get('short_story','')}

Backstory:
{profile.get('backstory','')}
"""
            st.download_button(
                label="⬇️ Download Persona (.txt)",
                data=persona_txt.encode("utf-8"),
                file_name=f"parsverse_persona_{d_name or 'anon'}.txt",
                mime="text/plain"
            )

        # Share (define role/locale first)
        role = profile.get("role", "") or "Citizen"
        locale = profile.get("locale", "") or d_region
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
