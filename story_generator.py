# story_generator.py
import os
import re
import json
from dotenv import load_dotenv

# --- Load .env (robust for OneDrive paths) ---
BASE_DIR = os.path.dirname(__file__)
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

# --- Streamlit Secrets -> os.environ (for Cloud) ---
try:
    import streamlit as st
    for k, v in st.secrets.items():
        os.environ.setdefault(k, str(v))
except Exception:
    pass

# --- Provider selection (groq / openai) ---
PROVIDER = (os.getenv("PROVIDER") or "groq").strip().lower()
if PROVIDER == "openai":
    from openai import OpenAI
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
elif PROVIDER == "groq":
    from groq import Groq
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-8b-8192")
else:
    raise ValueError(f"Unsupported PROVIDER: {PROVIDER}. Use 'groq' or 'openai'.")

# --- Transliteration mode ---
TRANSLIT_MODE = (os.getenv("TRANSLIT_MODE") or "modern").strip().lower()
if TRANSLIT_MODE not in ("modern", "old_persian"):
    TRANSLIT_MODE = "modern"

# ---------- Reference data ----------
REGIONS = [
    "Persis", "Media", "Parthia", "Sogdia", "Khwarezm",
    "Mazandaran", "Khorasan", "Zagros Mountains", "Caspian Sea", "Elam"
]

REGION_HINTS = {
    "Persis": "Achaemenid heartland: Pasargad (Pasargadae) and Parsa/Takht-e Jamshid (Persepolis); Kourosh (Cyrus), Dariush (Darius); farrah/farr (xvarənah, divine royal glory).",
    "Media": "Median highlands and early Iranian polities prior to Achaemenids; Hagmatāna/Hamadan (Ecbatana).",
    "Parthia": "Arsacid/Parthian era; horse archers, steppe-silk road links; Nisa; composite bows; satrapal ties.",
    "Sogdia": "Eastern Iranian merchants and caravans; Samarkand/Bukhara spheres; vibrant trade and Zoroastrian/Buddhist contacts.",
    "Khwarezm": "Lower Oxus/Amu Darya region; fortress-cities; water engineering; eastern Iranian culture.",
    "Mazandaran": "Caspian forests; Gilan/Mazandaran folklore; rugged mountains and sea mists; local dynasts.",
    "Khorasan": "Eastern marches; rising sun motif; legendary frontiers in the Shahnameh; desert winds and steppe edge.",
    "Zagros Mountains": "Highland passes, oak forests, pastoralism; old borderlands of Elamites and Medes; fortresses.",
    "Caspian Sea": "Caspian littoral; fishing, reeds and mist; Hyrcanian forests; humid coastal life.",
    "Elam": "Southwestern Iranian plateau prior to Achaemenids; Elamite heritage; Shush (Susa); brickwork and bull imagery."
}

REGION_TO_REALMS = {
    "Persis": ["Achaemenid", "Sasanian"],
    "Media": ["Median", "Achaemenid (early)"],
    "Parthia": ["Parthian (Arsacid)"],
    "Sogdia": ["Sogdian city-states"],
    "Khwarezm": ["Khwarazmian/Khwarezm"],
    "Mazandaran": ["Hyrcanian/Gorgan", "Local dynasts"],
    "Khorasan": ["Eastern Iranian frontiers", "Sasanian frontier satrapy"],
    "Zagros Mountains": ["Median", "Achaemenid satrapies"],
    "Caspian Sea": ["Hyrcanian/Gorgan"],
    "Elam": ["Elamite", "Achaemenid-era Shush"]
}

# ---------- Sanitizers: Indic terms ----------
BANNED = {
    r"\bkshatra\b": "xšaça (royal authority)",
    r"\bkṣatra\b": "xšaça (royal authority)",
    r"\bdharma\b": "",
    r"\bkarma\b": "",
    r"\bbrahman\b": "",
    r"\bchakra\b": "",
}
def sanitize_non_iranian(text: str) -> str:
    out = text
    for pat, repl in BANNED.items():
        out = re.sub(pat, repl, out, flags=re.IGNORECASE)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return out

# ---------- Transliteration maps ----------
# Modern Persian endonyms (with first-use exonym in parentheses)
GREEK_TO_PERSIAN_MODERN = {
    r"\bZoroaster\b": "Zarathustra",
    r"\bMithras\b": "Mithra",
    r"\bAnaitis\b": "Anāhitā",
    r"\bCyrus\b": "Kourosh (Cyrus)",
    r"\bDarius\b": "Dariush (Darius)",
    r"\bXerxes\b": "Khashayarsha (Xerxes)",
    r"\bArtaxerxes\b": "Ardeshir (Artaxerxes)",
    r"\bPersepolis\b": "Parsa / Takht-e Jamshid (Persepolis)",
    r"\bPasargadae\b": "Pasargad (Pasargadae)",
    r"\bEcbatana\b": "Hagmatāna / Hamadan (Ecbatana)",
    r"\bHyrcania\b": "Gorgan / Varkāna (Hyrcania)",
    r"\bSusa\b": "Shush (Susa)",
    r"\bCtesiphon\b": "Tisfun (Ctesiphon)",
}

# Old Persian / scholarly forms (without modern parentheses)
GREEK_TO_PERSIAN_OLD = {
    r"\bZoroaster\b": "Zaraθuštra",
    r"\bMithras\b": "Miθra",
    r"\bAnaitis\b": "Anāhitā",
    r"\bCyrus\b": "Kūruš",
    r"\bDarius\b": "Dārayavahuš",
    r"\bXerxes\b": "Xšayāršā",
    r"\bArtaxerxes\b": "Artaxšaçā",
    r"\bPersepolis\b": "Pārsa",
    r"\bPasargadae\b": "Paθragadā",
    r"\bEcbatana\b": "Haŋgmatana",
    r"\bHyrcania\b": "Varkāna",
    r"\bSusa\b": "Ūva",
    r"\bCtesiphon\b": "Tyspwn / Tīsapōn",  # scholarly reconstructions vary
}

def prefer_persian_forms(text: str) -> str:
    mapping = GREEK_TO_PERSIAN_MODERN if TRANSLIT_MODE == "modern" else GREEK_TO_PERSIAN_OLD
    out = text
    for pat, repl in mapping.items():
        out = re.sub(pat, repl, out, flags=re.IGNORECASE)
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out

# ---------- Prompts ----------
def _build_prompt(name: str, region: str, style: str = "Epic") -> str:
    hint = REGION_HINTS.get(region, "")
    translit_note = "Prefer IRANIAN ENDONYMS; if you include the Greek/Latin exonym, show it once in parentheses." \
        if TRANSLIT_MODE == "modern" else \
        "Use Old Persian/Avestan scholarly forms where applicable; avoid Greek/Latin exonyms."
    return f"""
You are a cultural historian and storyteller of ancient Iran.
Write a short persona scroll (4–5 sentences) about {name}, set in the historical region of {region}.

Context for accuracy: {hint}

STRICT RULES:
- Use ONLY Iranian/Persian terminology (Old Persian, Avestan, Middle Persian/Pahlavi, New Persian).
- {translit_note}
- DO NOT use Indic/Sanskrit terms (kshatra/kṣatra, dharma, karma, etc.).
- Prefer clear modern English; if you use a Persian term, gloss it once in brackets, e.g., farrah/farr (divine glory), xšaça (royal authority).
- Keep the tone {style.lower()} and culturally faithful to Iranian history/myth.
- Avoid anachronisms and cross-cultural mixing unless explicitly Persianized and accurate.
- Return ONLY the scroll text (no headings).
"""

def _build_profile_prompt(name: str, region: str, age: int, gender: str, traits: list[str], hobby: str, style: str) -> str:
    region_hint = REGION_HINTS.get(region, "")
    realms = REGION_TO_REALMS.get(region, ["Iranian polity"])
    traits_str = ", ".join(traits) if traits else "balanced"
    translit_note = "Prefer Iranian endonyms; include Greek/Latin exonym once in parentheses." \
        if TRANSLIT_MODE == "modern" else \
        "Use Old Persian/Avestan scholarly forms; avoid exonyms."
    return f"""
You are a cultural historian and storyteller of ancient Iran. Create a **structured persona profile** for:
- Name: {name}
- Region: {region}
- Age: {age}
- Gender: {gender}
- Traits: {traits_str}
- Hobby/Work: {hobby}

Context for accuracy: {region_hint}
Likely realms to choose from (pick the best fit): {", ".join(realms)}.

STRICT RULES:
- Use ONLY Iranian/Persian terminology (Old Persian, Avestan, Middle Persian/Pahlavi, New Persian).
- {translit_note}
- DO NOT use Indic/Sanskrit terms (kshatra/kṣatra, dharma, karma, etc.).
- Keep the tone {style.lower()}, culturally faithful to Iranian history/myth.
- Be specific about **kingdom**, **city/locale**, and **role/job**; link the choice to traits/hobby.
- Return ONLY valid JSON (no codeblock, no prose) with keys:
  {{
    "kingdom": "...",
    "locale": "...",
    "role": "...",
    "titles": ["...", "..."],
    "symbols": ["...", "..."],
    "artifact": "...",
    "backstory": "...",
    "motto": "..."
  }}
- If you use Persian terms (e.g., farrah/farr, xšaça), briefly gloss in brackets the first time.
"""

# ---------- Generators ----------
def generate_parsverse_myth(name: str, region: str, style: str = "Epic") -> str:
    if not name or not region:
        raise ValueError("Both name and region are required.")
    prompt = _build_prompt(name, region, style)

    if PROVIDER == "openai":
        resp = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.85,
            max_tokens=320,
        )
        result = resp.choices[0].message.content.strip()
    elif PROVIDER == "groq":
        resp = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.85,
            max_tokens=320,
        )
        result = resp.choices[0].message.content.strip()
    else:
        raise RuntimeError("No valid provider configured.")

    result = sanitize_non_iranian(result)
    result = prefer_persian_forms(result)
    return result

def generate_parsverse_profile(name: str, region: str, age: int, gender: str, traits: list[str], hobby: str, style: str = "Epic") -> dict:
    if not name or not region:
        raise ValueError("Name and region are required.")
    prompt = _build_profile_prompt(name, region, age, gender, traits, hobby, style)

    if PROVIDER == "openai":
        resp = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=900,
        )
        raw = resp.choices[0].message.content.strip()
    elif PROVIDER == "groq":
        resp = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=900,
        )
        raw = resp.choices[0].message.content.strip()
    else:
        raise RuntimeError("No valid provider configured.")

    # Clean potential code fences
    raw_clean = raw.strip()
    for fence in ("```json", "```"):
        if raw_clean.startswith(fence):
            raw_clean = raw_clean[len(fence):].strip()
    if raw_clean.endswith("```"):
        raw_clean = raw_clean[:-3].strip()

    # Parse JSON (fallback to dumping text into backstory)
    try:
        data = json.loads(raw_clean)
    except Exception:
        data = {
            "kingdom": "",
            "locale": "",
            "role": "",
            "titles": [],
            "symbols": [],
            "artifact": "",
            "backstory": raw_clean,
            "motto": ""
        }

    # Sanitize all text fields
    def clean(s: str) -> str:
        if not isinstance(s, str): return s
        s = sanitize_non_iranian(s)
        s = prefer_persian_forms(s)
        return s

    for key in ["kingdom", "locale", "role", "artifact", "backstory", "motto"]:
        if key in data and isinstance(data[key], str):
            data[key] = clean(data[key])

    for key in ["titles", "symbols"]:
        if key in data and isinstance(data[key], list):
            data[key] = [clean(x) for x in data[key]]

    return data

# ---------- Local test ----------
if __name__ == "__main__":
    print("Provider:", PROVIDER)
    print("Translit mode:", TRANSLIT_MODE)
    key_preview = (os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY") or "")[:8]
    print("API key starts with:", key_preview if key_preview else None)

    print("\n--- Myth Test ---")
    print(generate_parsverse_myth("Daniel", "Persis", "Royal"))

    print("\n--- Profile Test ---")
    profile = generate_parsverse_profile(
        name="Roxana",
        region="Khorasan",
        age=24,
        gender="Female",
        traits=["brave", "curious"],
        hobby="archer",
        style="Mystic"
    )
    print(json.dumps(profile, indent=2, ensure_ascii=False))
