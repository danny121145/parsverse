# story_generator.py
import os
import re
from dotenv import load_dotenv

# --- Force-load .env from this file's directory (avoids OneDrive path quirks) ---
BASE_DIR = os.path.dirname(__file__)
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

# --- Provider selection (groq / openai) ---
PROVIDER = (os.getenv("PROVIDER") or "groq").strip().lower()

# Clients are imported lazily so you only need the lib for the provider you use
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

# --- Regions list (used by Streamlit UI too) ---
REGIONS = [
    "Persis", "Media", "Parthia", "Sogdia", "Khwarezm",
    "Mazandaran", "Khorasan", "Zagros Mountains", "Caspian Sea", "Elam"
]

# --- Region hints to steer the model toward accurate Iranian context ---
REGION_HINTS = {
    "Persis": "Achaemenid heartland: Pasargadae and Persepolis; Cyrus the Great, Darius; farr/farrah (xvarənah, divine royal glory).",
    "Media": "Median highlands and early Iranian polities prior to Achaemenids; Ecbatana traditions.",
    "Parthia": "Arsacid/Parthian era; horse archers, steppe-silk road links; Nisa; composite bows; satrapal ties.",
    "Sogdia": "Eastern Iranian merchants and caravans; Samarkand/Bukhara spheres; vibrant trade and Zoroastrian/Buddhist contacts.",
    "Khwarezm": "Lower Oxus/Amu Darya region; fortress-cities; water engineering; eastern Iranian culture.",
    "Mazandaran": "Caspian forests; Gilan/Mazandaran folklore; rugged mountains and sea mists; local dynasts.",
    "Khorasan": "Eastern marches; rising sun motif; legendary frontiers in the Shahnameh; desert winds and steppe edge.",
    "Zagros Mountains": "Highland passes, oak forests, pastoralism; old borderlands of Elamites and Medes; fortresses.",
    "Caspian Sea": "Caspian littoral; fishing, reeds and mist; Hyrcanian forests; humid coastal life.",
    "Elam": "Southwestern Iranian plateau prior to Achaemenids; Elamite heritage; Susa; brickwork and bull imagery."
}

# --- Non-Iranian terms we want to block or replace (to avoid Indic bleed) ---
BANNED = {
    r"\bkshatra\b": "xšaça (royal authority)",  # Sanskrit form → Iranian gloss
    r"\bkṣatra\b": "xšaça (royal authority)",
    r"\bdharma\b": "",                          # remove if it slips in
    r"\bkarma\b": "",
    r"\bbrahman\b": "",
    r"\bchakra\b": "",
}

def sanitize_non_iranian(text: str) -> str:
    out = text
    for pat, repl in BANNED.items():
        out = re.sub(pat, repl, out, flags=re.IGNORECASE)
    # collapse surplus spaces/newlines after removals
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return out

import re

GREEK_TO_PERSIAN = {
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

def prefer_persian_forms(text: str) -> str:
    out = text
    for pat, repl in GREEK_TO_PERSIAN.items():
        out = re.sub(pat, repl, out, flags=re.IGNORECASE)
    # tidy duplicate spaces/parentheses if any
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out

def _build_prompt(name: str, region: str, style: str = "Epic") -> str:
    hint = REGION_HINTS.get(region, "")
    return f"""
You are a cultural historian and storyteller of ancient Iran.
Write a short persona scroll (4–5 sentences) about {name}, set in the historical region of {region}.

Context for accuracy: {hint}

STRICT RULES:
- Use ONLY Iranian/Persian terminology (Old Persian, Avestan, Middle Persian/Pahlavi, New Persian).
- Prefer IRANIAN ENDONYMS; if you include the more common Greek/Latin exonym, put it once in parentheses after the first mention. Examples:
  - Zarathustra (not Zoroaster)
  - Mithra (not Mithras)
  - Anāhitā (not Anaitis)
  - Kourosh (Cyrus) • Dariush (Darius) • Khashayarsha (Xerxes) • Ardeshir (Artaxerxes)
  - Parsa / Takht-e Jamshid (Persepolis), Pasargad (Pasargadae), Hagmatāna/Hamadan (Ecbatana),
    Gorgan/Varkāna (Hyrcania), Shush (Susa), Tisfun (Ctesiphon)
- DO NOT use Indic/Sanskrit terms (e.g., dharma, karma, kshatra/kṣatra).
- Use clear modern English; gloss any Persian term in brackets if needed (e.g., farrah/farr (divine glory)).
- Keep the tone {style.lower()} and culturally faithful to Iranian history/myth.
- Return ONLY the scroll text.
"""

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
        result = sanitize_non_iranian(result)
        result = prefer_persian_forms(result)
        return result

    if PROVIDER == "groq":
        resp = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.85,
            max_tokens=320,
        )
        result = resp.choices[0].message.content.strip()
        result = sanitize_non_iranian(result)
        result = prefer_persian_forms(result)
        return result

    raise RuntimeError("No valid provider configured.")

# --- Quick local test ---
if __name__ == "__main__":
    provider = PROVIDER
    key_preview = (os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY") or "")[:8]
    print("Provider:", provider)
    print("API key starts with:", key_preview if key_preview else None)

    # try a couple regions/styles
    print("\n--- Test 1 ---")
    print(generate_parsverse_myth("Daniel", "Persis", "Royal"))
    print("\n--- Test 2 ---")
    print(generate_parsverse_myth("Roxana", "Khorasan", "Mystic"))
