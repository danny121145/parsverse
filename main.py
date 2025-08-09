# main.py
import os
import json
import random
import urllib.parse
import streamlit as st
from story_generator import (
    generate_parsverse_myth,
    generate_parsverse_profile,
    REGIONS,
)

# ------------------ Config & Branding ------------------
APP_URL = os.getenv("APP_URL", "").strip()  # set in Streamlit Secrets for nicer share links
st.set_page_config(page_title="ParsVerse – Myth & Persona", page_icon="🏛️", layout="centered")

BRAND_CSS = """
<style>
:root{
  --bg:#fffdf7;
  --card:#fdf6e3;
  --ink:#2a2a2a;
  --gold:#c2b280;
  --accent:#0f766e; /* turquoise-ish */
}
html, body, [data-testid="stAppViewContainer"]{
  background:var(--bg);
}
.block-container{
  padding-top:2rem;
}
.pars-card{
  background:var(--card);
  padding:22px;
  border:2px solid var(--gold);
  border-radius:14px;
  font-family:Georgia,serif;
  box-shadow:0 8px 24px rgba(0,0,0,0.06);
}
.pars-scroll{
  background:var(--card);
  padding:18px;
  border:1px solid #d8caa1;
  border-radius:10px;
  font-family:Georgia,serif;
}
.badge{
  display:inline-block;
  padding:4px 10px;
  border:1px solid var(--gold);
  border-radius:999px;
  background:#fff;
  font-size:12px;
  margin-left:8px;
}
.sharebar a{
  text-decoration:none;
  margin-right:10px;
}
.copybtn{
  border:1px solid var(--gold);
  padding:6px 10px;
  border-radius:8px;
  background:#fff;
  cursor:pointer;
}
h1.title{
  text-align:center;margin:0 0 6px 0;
}
.subtitle{
  text-align:center;margin-top:6px;margin-bottom:0;
}
.divider{height:1px;background:#e6dcc0;margin:18px 0;}
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
        pass  # Cloud environments may be ephemeral; it's fine for MVP

def bump_counter(kind):
    data = _load_counts()
    data["total"] = data.get("total", 0) + 1
    if kind == "myth":
        data["myths"] = data.get("myths", 0) + 1
    elif kind == "persona":
        data["personas"] = data.get("personas", 0) + 1
    _save_counts(data)
    return data

GLOBAL_COUNTS = _load_counts()

# ------------------ Did you know facts ------------------
FACTS = [
    "“Farr / Farrah (xvarənah)” denotes divine royal glory in Iranian tradition.",
    "Takht-e Jamshid (Parsa/Persepolis) carries trilingual inscriptions in Old Persian, Elamite, and Babylonian.",
    "Kourosh (Cyrus) founded Pasargad (Pasargadae), the early Achaemenid capital.",
    "Hagmatāna (Hamadan/Ecbatana) is tied to Median royal heritage.",
    "Tisfun (Ctesiphon) was a major imperial capital on the Tigris in late antique Iran.",
    "The Shahnameh preserves epic cycles of Iranian heroes like Rostam from Sistan/Zabulistan.",
    "Sogdian merchants linked Iran to the Silk Roads via Samarkand and Bukhara.",
]

# ------------------ Header ------------------
st.markdown("""
<h1 class="title">🏛️ ParsVerse</h1>
<p class="subtitle">Create your Persian-inspired <strong>myth</strong> or a <strong>detailed persona</strong> (kingdom, locale, role, backstory).
<span class="badge">Total legends woven: {total}</span>
</p>
""".format(total=GLOBAL_COUNTS.get("total", 0)), unsafe_allow_html=True)

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
        q_submit = st.form_submit_button("Generate Myth")

    if q_submit:
        if not q_name or not q_region:
            st.warning("Please enter a name and choose a region.")
        else:
            tip = random.choice(FACTS)
            with st.spinner(f"Weaving your legend… (Did you know? {tip})"):
                myth = generate_parsverse_myth(q_name, q_region, q_style)

            st.success("Your scroll is ready!")
            st.markdown('<div class="pars-card"><h3 style="text-align:center;margin-top:0;">🪶 ParsVerse Scroll</h3></div>', unsafe_allow_html=True)
            st.markdown(f"<div class='pars-scroll'><p style='font-size:18px;line-height:1.7;white-space:pre-wrap;'>{myth}</p></div>", unsafe_allow_html=True)

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
            st.markdown(
                f"<div class='sharebar' style='margin-top:8px;'>"
                f"<a href='{tw_url}' target='_blank'>🐦 Share on X</a>"
                f"</div>",
                unsafe_allow_html=True
            )

            # Copy to clipboard (simple JS)
            st.markdown("""
            <button class="copybtn" onclick="navigator.clipboard.writeText(document.getElementById('mythtext').innerText)">Copy myth to clipboard</button>
            <pre id="mythtext" style="position:absolute;left:-9999px;white-space:pre-wrap;">{}</pre>
            """.format(myth.replace("<","&lt;").replace(">","&gt;")), unsafe_allow_html=True)

            # bump counters
            GLOBAL_COUNTS = bump_counter("myth")
            st.experimental_rerun()  # refresh the header badge

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

    d_submit = st.form_submit_button("Generate Detailed Persona")

if d_submit:
    if not d_name or not d_region:
        st.warning("Please enter a name and choose a region.")
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

        # Render persona card
        st.success("Your persona is ready!")
        st.markdown('<div class="pars-card"><h3 style="text-align:center;margin-top:0;">👑 Persona Dossier</h3></div>', unsafe_allow_html=True)

        # Title block
        role = profile.get("role", "") or "Citizen"
        locale = profile.get("locale", "") or d_region
        titles = profile.get("titles", []) or []
        st.markdown(
            f"<h4 style='text-align:center;margin:8px 0 2px 0;'>{role} of {locale}</h4>"
            f"<p style='text-align:center;margin-top:0;'><em>{', '.join(titles)}</em></p>",
            unsafe_allow_html=True
        )

        # Backstory
        st.markdown(f"<div class='pars-scroll'><p style='font-size:18px;line-height:1.7;white-space:pre-wrap;'>{profile.get('backstory','')}</p></div>", unsafe_allow_html=True)

        # Quick facts
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

        # ---- Downloads ----
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

        # ---- Share ----
        share_text = f"My ParsVerse persona: {role} of {locale} — {APP_URL}" if APP_URL else f"My ParsVerse persona: {role} of {locale}"
        tw_url = f"https://twitter.com/intent/tweet?text={urllib.parse.quote_plus(share_text)}"
        st.markdown(
            f"<div class='sharebar' style='margin-top:8px;'>"
            f"<a href='{tw_url}' target='_blank'>🐦 Share on X</a>"
            f"</div>",
            unsafe_allow_html=True
        )

        # bump counters
        GLOBAL_COUNTS = bump_counter("persona")
        st.experimental_rerun()  # refresh header badge

st.caption("Tip: Traits + hobby/work guide the role, while region maps to a plausible Iranian realm. Endonyms are preferred; Indic/Greek exonyms are sanitized.")
