# main.py
import streamlit as st
from story_generator import (
    generate_parsverse_myth,
    generate_parsverse_profile,
    REGIONS,
)

st.set_page_config(page_title="ParsVerse – Myth & Persona", layout="centered")

# ---------- Header ----------
st.markdown("""
<h1 style="text-align:center;margin-bottom:0;">🏛️ ParsVerse</h1>
<p style="text-align:center;margin-top:6px;">
Create your Persian-inspired <strong>myth</strong> or a <strong>detailed persona dossier</strong> (kingdom, locale, role, backstory).
</p>
""", unsafe_allow_html=True)

st.divider()

# ========== Quick Myth ==========
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
            with st.spinner("Weaving your legend..."):
                myth = generate_parsverse_myth(q_name, q_region, q_style)

            st.success("Your scroll is ready!")
            st.markdown("""
            <div style="background:#fdf6e3;padding:22px;border:2px solid #c2b280;border-radius:12px;
                        font-family:Georgia,serif;box-shadow:0 8px 24px rgba(0,0,0,0.06);">
                <h3 style="text-align:center;margin-top:0;">🪶 ParsVerse Scroll</h3>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(
                f"<div style='background:#fdf6e3;padding:18px;border:1px solid #d8caa1;border-radius:10px;"
                f"font-family:Georgia,serif;'><p style='font-size:18px;line-height:1.7;white-space:pre-wrap;'>{myth}</p></div>",
                unsafe_allow_html=True
            )

st.divider()

# ========== Detailed Persona ==========
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
        with st.spinner("Consulting the court archives..."):
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
        st.markdown("""
        <div style="background:#fdf6e3;padding:22px;border:2px solid #c2b280;border-radius:12px;
                    font-family:Georgia,serif;box-shadow:0 8px 24px rgba(0,0,0,0.06);">
            <h3 style="text-align:center;margin-top:0;">👑 Persona Dossier</h3>
        </div>
        """, unsafe_allow_html=True)

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
        st.markdown(
            f"<div style='background:#fdf6e3;padding:18px;border:1px solid #d8caa1;border-radius:10px;"
            f"font-family:Georgia,serif;'><p style='font-size:18px;line-height:1.7;white-space:pre-wrap;'>{profile.get('backstory','')}</p></div>",
            unsafe_allow_html=True
        )

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

st.caption("Tip: Traits + hobby/work guide the role, while region maps to a plausible Iranian realm. Endonyms are preferred; Indic/Greek exonyms are sanitized.")
