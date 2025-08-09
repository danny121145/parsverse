# main.py
import streamlit as st
from story_generator import generate_parsverse_myth, REGIONS

st.set_page_config(page_title="ParsVerse – Myth Generator", layout="centered")

st.markdown("""
# 🏛️ ParsVerse
Create your **Persian-inspired myth** as a beautiful scroll.
""")

with st.form("parsverse_form"):
    name = st.text_input("Your name")
    region = st.selectbox("Choose a historical region", REGIONS, index=6)  # default Khorasan
    style = st.selectbox("Style / tone", ["Epic", "Mystic", "Royal", "Poet"])
    submitted = st.form_submit_button("Generate My Myth")

if submitted:
    if not name or not region:
        st.warning("Please fill in your name and region.")
    else:
        with st.spinner("Weaving your legend..."):
            myth = generate_parsverse_myth(name, region, style)

        st.success("Your scroll is ready!")
        st.markdown("---")
        st.markdown(f"""
        <div style="background:#fdf6e3;padding:22px;border:2px solid #c2b280;border-radius:12px;
                    font-family:Georgia,serif;box-shadow:0 8px 24px rgba(0,0,0,0.06);">
            <h3 style="text-align:center;margin-top:0;">🪶 Your ParsVerse Scroll</h3>
            <p style="font-size:18px;line-height:1.7;white-space:pre-wrap;">{myth}</p>
        </div>
        """, unsafe_allow_html=True)

st.caption("Tip: Try different regions/styles for totally new vibes.")
