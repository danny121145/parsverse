# story_generator.py
import os
import re
import json
from dotenv import load_dotenv

# --- Load .env (local dev) ---
BASE_DIR = os.path.dirname(__file__)
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

# --- Streamlit Secrets -> env (Streamlit Cloud) ---
try:
    import streamlit as st
    for k, v in st.secrets.items():
        os.environ.setdefault(k, str(v))
except Exception:
    pass

# ================== Provider (lazy init) ==================
PROVIDER = (os.getenv("PROVIDER") or "groq").strip().lower()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-8b-8192")

_openai_client = None
_groq_client = None

def _get_client():
    """Lazy-create and cache the API client so imports never crash."""
    global _openai_client, _groq_client
    if PROVIDER == "openai":
        if _openai_client is None:
            from openai import OpenAI
            key = os.getenv("OPENAI_API_KEY")
            if not key:
                raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env or Streamlit Secrets.")
            _openai_client = OpenAI(api_key=key)
        return "openai", _openai_client
    elif PROVIDER == "groq":
        if _groq_client is None:
            from groq import Groq
            key = os.getenv("GROQ_API_KEY")
            if not key:
                raise RuntimeError("GROQ_API_KEY is not set. Add it to .env or Streamlit Secrets.")
            _groq_client = Groq(api_key=key)
        return "groq", _groq_client
    else:
        raise RuntimeError("Unsupported PROVIDER. Use 'groq' or 'openai'.")

# ================== Transliteration mode ==================
TRANSLIT_MODE = (os.getenv("TRANSLIT_MODE") or "modern").strip().lower()
if TRANSLIT_MODE not in ("modern", "old_persian"):
    TRANSLIT_MODE = "modern"

# ================== Reference data ==================
REGIONS = [
    "Persis", "Media", "Parthia", "Sogdia", "Khwarezm",
    "Mazandaran", "Khorasan", "Zagros Mountains", "Caspian Sea", "Elam"
]
KNOWN_REGIONS = set(REGIONS)

def _normalize_region(region: str) -> str:
    r = (region or "").strip()
    return r if r in KNOWN_REGIONS else "Persis"

REGION_HINTS = {
    "Persis": "Achaemenid heartland: Pasargad (Pasargadae) and Parsa/Takht-e Jamshid (Persepolis); Kourosh (Cyrus), Dariush (Darius); farrah/farr (xvarənah, divine royal glory).",
    "Media": "Median highlands and early Iranian polities prior to Achaemenids; Hagmatāna/Hamadan (Ecbatana).",
    "Parthia": "Arsacid/Parthian era; horse archers, steppe-silk road links; Nisa; composite bows; satrapal ties.",
    "Sogdia": "Eastern Iranian merchants and caravans; Samarkand/Bukhara spheres; vibrant trade and Zoroastrian/Buddhist contacts.",
    "Khwarezm": "Lower Oxus/Amu Darya region; fortress-cities; water engineering; eastern Iranian culture.",
    "Mazandaran": "Caspian forests; Gilan/Mazandaran folklore; rugged mountains and sea mists; local dynasts.",
    "Khorasan": "Eastern marches; rising sun motif; legendary frontiers in the Shahnameh; desert winds and steppe edge.",
    "Zagros Mountains": "Highland passes, oak forests, pastoralism; old borderlands of Medes and Elam; fortresses.",
    "Caspian Sea": "Caspian littoral; fishing, reeds and mist; Hyrcanian forests; humid coastal life.",
    "Elam": "Southwestern Iranian plateau prior to Achaemenids; Elamite heritage; Shush (Susa); brickwork and bull imagery."
}

# Richer regional word-banks to steer flavor
REGION_LEXICON = {
    "Persis": [
        "Parsa", "Pasargad", "Takht-e Jamshid", "farrah/farr (divine glory)",
        "xšaça (royal authority)", "apadana hall", "inscribed cliff relief"
    ],
    "Media": [
        "Hagmatāna", "Hamadan", "Median highlands", "early satrapy",
        "horse-breeding meadows", "mountain citadel", "woven felt cloaks"
    ],
    "Parthia": [
        "Nisa", "cataphract cavalry", "steppe frontier", "satrap",
        "composite bow", "heavy lamellar armor", "royal caravanserai"
    ],
    "Sogdia": [
        "Samarkand", "Bukhara", "Silk Road caravan", "merchant seals",
        "Sogdian script", "sandalwood and lapis trade", "bazaar courtyards"
    ],
    "Khwarezm": [
        "Oxus (Amu Darya)", "irrigation canals", "fortress-city walls",
        "kurgan mounds", "mudbrick citadel", "oasis agriculture"
    ],
    "Mazandaran": [
        "Hyrcanian forest", "Caspian mist", "reedboats and fishing",
        "rice terraces", "pomegranate orchards", "leopard folklore"
    ],
    "Khorasan": [
        "eastern frontier", "sunrise motif", "desert wind", "oasis towns",
        "caravan strongholds", "frontier garrisons", "Shahnameh marches"
    ],
    "Zagros Mountains": [
        "high passes", "oak woodlands", "pastoral camps",
        "rock-cut reliefs", "mountain fortresses", "goat-hair tents"
    ],
    "Caspian Sea": [
        "reeds and lagoons", "sturgeon fisheries", "humid coast",
        "Hyrcanian wood", "sea mists", "coastal watchtowers"
    ],
    "Elam": [
        "Shush (Susa)", "glazed brick reliefs", "bull protomes",
        "Elamite scribes", "ziggurat platforms", "canal embankments"
    ],
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

# ================== Sanitizers & Guards ==================
BANNED_MAP = {
    r"\bkshatra\b": "xšaça (royal authority)",
    r"\bkṣatra\b": "xšaça (royal authority)",
    r"\bdharma\b": "",
    r"\bkarma\b": "",
    r"\bsamsara\b": "",
    r"\bmoksha\b": "",
    r"\bmantra\b": "",
    r"\btantra\b": "",
    r"\bsutra\b": "",
    r"\bchakra\b": "",
    r"\bveda(s)?\b": "",
    r"\bvedic\b": "",
    r"\batman\b": "",
    r"\bātman\b": "",
    r"\bbrahma(n)?\b": "",
    r"\bbrahmin\b": "",
    r"\bindra\b": "",
    r"\bshiva\b": "",
    r"\bvishnu\b": "",
    r"\bganesha\b": "",
    r"\blakshmi\b": "",
    r"\bpurusha\b": "",
    r"\byuga\b": "",
    r"\braja(h)?\b": "",
    r"\bhindu(ism|ist)?\b": "",
}
BANNED_COMPILED = [(re.compile(pat, re.IGNORECASE), repl) for pat, repl in BANNED_MAP.items()]

def sanitize_non_iranian(text: str) -> str:
    out = text
    for rx, repl in BANNED_COMPILED:
        out = rx.sub(repl, out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return out

def contains_banned(text: str) -> bool:
    return any(rx.search(text) for rx, _ in BANNED_COMPILED)

# Exonyms → preferred Persian forms
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
    r"\bCtesiphon\b": "Tyspwn / Tīsapōn",
}

def prefer_persian_forms(text: str) -> str:
    mapping = GREEK_TO_PERSIAN_MODERN if TRANSLIT_MODE == "modern" else GREEK_TO_PERSIAN_OLD
    out = text
    for pat, repl in mapping.items():
        out = re.sub(pat, repl, out, flags=re.IGNORECASE)
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out

# ================== Prompts ==================
FORBIDDEN_LINE = (
    "Forbidden terms: kshatra/kṣatra, dharma, karma, samsara, moksha, mantra, tantra, sutra, chakra, "
    "Veda/Vedic, atman, brahma/brahman/brahmin, Indra, Shiva, Vishnu, Ganesha, Lakshmi, Purusha, yuga, raja/rajah, Hindu/Hinduism."
)

def _build_prompt(name: str, region: str, style: str = "Epic") -> str:
    region = _normalize_region(region)
    hint = REGION_HINTS.get(region, "")
    lex = ", ".join(REGION_LEXICON.get(region, []))
    translit_note = (
        "Prefer IRANIAN endonyms; if you include a Greek/Latin exonym, show it once in parentheses."
        if TRANSLIT_MODE == "modern" else
        "Use Old Persian/Avestan scholarly forms; avoid Greek/Latin exonyms."
    )
    return f"""
You are a cultural historian and storyteller of ancient Iran.
Write a short persona scroll (4–5 sentences) about {name}, set in the historical region of {region}.

Context for accuracy: {hint}
Use a few region-appropriate motifs/terms when relevant: {lex}

STRICT RULES:
- Use ONLY Iranian/Persian terminology (Old Persian, Avestan, Middle Persian/Pahlavi, New Persian).
- {translit_note}
- DO NOT use non-Iranian/Indic terms. {FORBIDDEN_LINE}
- Prefer clear modern English; if you use a Persian term, gloss it once in brackets (e.g., farrah/farr (divine glory), xšaça (royal authority)).
- Keep the tone {style.lower()} and culturally faithful to Iranian history/myth.
- Avoid anachronisms and cross-cultural mixing unless explicitly Persianized and accurate.
- Return ONLY the scroll text (no headings).
""".strip()

def _build_profile_prompt(
    name: str,
    region: str,
    age: int,
    gender: str,
    traits: list[str],
    hobby: str,
    style: str
) -> str:
    region = _normalize_region(region)
    region_hint = REGION_HINTS.get(region, "")
    lex = ", ".join(REGION_LEXICON.get(region, []))
    realms = REGION_TO_REALMS.get(region, ["Iranian polity"])
    traits_str = ", ".join(traits) if traits else "balanced"
    translit_note = (
        "Prefer Iranian endonyms; include Greek/Latin exonym once in parentheses."
        if TRANSLIT_MODE == "modern" else
        "Use Old Persian/Avestan scholarly forms; avoid exonyms."
    )
    return f"""
You are a cultural historian and storyteller of ancient Iran. Create a **personal, realistic persona profile** for the user with clear, concrete details.

INPUTS
- Name: {name}
- Region: {region}
- Age: {age}
- Gender: {gender}
- Traits: {traits_str}
- Hobby/Work: {hobby}

CONTEXT
- Region hint: {region_hint}
- Regional lexicon to sprinkle when relevant: {lex}
- Likely realms to choose from (pick the best fit): {", ".join(realms)}.

TONE & STYLE
- Speak **to** the user (2nd person) as if describing their life.
- Prioritize **clarity and realism** over flowery language.
- {translit_note}
- DO NOT use non-Iranian/Indic terms. {FORBIDDEN_LINE}
- Use only Iranian/Persian terminology (Old Persian, Avestan, Middle Persian/Pahlavi, New Persian).
- If you use a Persian term, gloss it once in brackets (e.g., farrah/farr (divine glory), xšaça (royal authority)).

OUTPUT
Return ONLY valid JSON (no extra text, no code fences) with these keys exactly:
{{
  "kingdom": "Specific Iranian realm (e.g., Achaemenid, Median, Parthian, Sogdian city-states, Sasanian)",
  "locale": "City/locale (e.g., Hagmatāna / Hamadan (Ecbatana))",
  "role": "Clear role/job title in that kingdom tied to traits/hobby",
  "favorite_food": "A plausible dish or staple for that region/era",
  "hobby": "A concrete hobby past-time tied to inputs",
  "friends": "A short phrase describing your social circle (e.g., caravan merchants, scribes, archers)",
  "titles": ["Short epithets or honorifics"],
  "symbols": ["2–4 meaningful symbols"],
  "artifact": "One signature item you carry/use",
  "short_story": "4–6 sentences: a small moment from your life in that setting; grounded and readable.",
  "backstory": "5–8 sentences: who you are, how you fit into the realm, and how traits map to your role.",
  "motto": "A short motto that fits your persona"
}}
""".strip()

# ================== Generators (with retry & sanitization) ==================
def generate_parsverse_myth(name: str, region: str, style: str = "Epic") -> str:
    if not name or not region:
        raise ValueError("Both name and region are required.")

    prompt = _build_prompt(name, region, style)
    max_tries = 3
    last_text = ""

    for _ in range(max_tries):
        provider, client = _get_client()
        if provider == "openai":
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.85,
                max_tokens=320,
            )
            raw = resp.choices[0].message.content.strip()
        else:  # groq
            resp = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.85,
                max_tokens=320,
            )
            raw = resp.choices[0].message.content.strip()

        cleaned = prefer_persian_forms(sanitize_non_iranian(raw))
        last_text = cleaned
        if not contains_banned(cleaned):
            return cleaned

        prompt += (
            "\n\nREVISION INSTRUCTIONS: Your previous draft included forbidden Indic terms. "
            "Regenerate the scroll using ONLY Iranian terminology; strictly obey the forbidden list."
        )

    return last_text  # fallback

def generate_parsverse_profile(
    name: str,
    region: str,
    age: int,
    gender: str,
    traits: list[str],
    hobby: str,
    style: str = "Epic"
) -> dict:
    if not name or not region:
        raise ValueError("Name and region are required.")
    prompt = _build_profile_prompt(name, region, age, gender, traits, hobby, style)

    max_tries = 3
    last_data = None
    last_concat = ""

    for _ in range(max_tries):
        provider, client = _get_client()
        if provider == "openai":
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=950,
            )
            raw = resp.choices[0].message.content.strip()
        else:  # groq
            resp = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=950,
            )
            raw = resp.choices[0].message.content.strip()

        # strip code fences if present
        raw_clean = raw.strip()
        for fence in ("```json", "```"):
            if raw_clean.startswith(fence):
                raw_clean = raw_clean[len(fence):].strip()
        if raw_clean.endswith("```"):
            raw_clean = raw_clean[:-3].strip()

        # parse JSON or wrap fallback
        try:
            data = json.loads(raw_clean)
        except Exception:
            data = {
                "kingdom": "",
                "locale": "",
                "role": "",
                "favorite_food": "",
                "hobby": hobby,
                "friends": "",
                "titles": [],
                "symbols": [],
                "artifact": "",
                "short_story": "",
                "backstory": raw_clean,
                "motto": ""
            }

        def clean(s: str) -> str:
            if not isinstance(s, str):
                return s
            return prefer_persian_forms(sanitize_non_iranian(s))

        # clean string fields
        for key in [
            "kingdom","locale","role","favorite_food","hobby",
            "friends","artifact","short_story","backstory","motto"
        ]:
            if key in data and isinstance(data[key], str):
                data[key] = clean(data[key])

        # clean list fields
        for key in ["titles","symbols"]:
            if key in data and isinstance(data[key], list):
                data[key] = [clean(x) for x in data[key]]

        # banned check across concatenated text fields
        last_data = data
        last_concat = " ".join([
            data.get("kingdom",""), data.get("locale",""), data.get("role",""),
            data.get("favorite_food",""), data.get("hobby",""), data.get("friends",""),
            " ".join(data.get("titles",[])), " ".join(data.get("symbols",[])),
            data.get("artifact",""), data.get("short_story",""),
            data.get("backstory",""), data.get("motto","")
        ])

        if not contains_banned(last_concat):
            return data

        # tighten constraints and retry
        prompt += (
            "\n\nREVISION INSTRUCTIONS: Your previous draft included forbidden Indic terms. "
            "Regenerate STRICT JSON using ONLY Iranian terminology; strictly obey the forbidden list."
        )

    return last_data or {
        "backstory": "Generation failed after retries. Please try again.",
        "short_story": ""
    }

# ---- Back-compat / typo aliases (optional) ----
def parseverse_myth(*args, **kwargs):  # common typo
    return generate_parsverse_myth(*args, **kwargs)

def generate_parseverse_myth(*args, **kwargs):  # another typo form
    return generate_parsverse_myth(*args, **kwargs)

# ---- Local smoke test ----
if __name__ == "__main__":
    print("Provider:", PROVIDER, "| Translit mode:", TRANSLIT_MODE)
    key_preview = (os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY") or "")[:8]
    print("API key starts with:", key_preview if key_preview else None)

    print("\n--- Myth Test ---")
    try:
        print(generate_parsverse_myth("Daniel", "Persis", "Royal"))
    except Exception as e:
        print("Myth error:", e)

    print("\n--- Profile Test ---")
    try:
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
    except Exception as e:
        print("Profile error:", e)
