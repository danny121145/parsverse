# story_generator.py
import os
import re
import json
import base64
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

# ================== Images provider (optional) ==================
# Supported providers: "openai", "xai" (Grok), "huggingface"
IMG_PROVIDER = (os.getenv("IMG_PROVIDER") or "huggingface").strip().lower()

# OpenAI
OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")

# xAI / Grok
XAI_IMAGE_MODEL = os.getenv("XAI_IMAGE_MODEL", "grok-2-image")

# Hugging Face (good defaults: SDXL base or SDXL Turbo)
HF_IMAGE_MODEL = os.getenv("HF_IMAGE_MODEL", "stabilityai/stable-diffusion-xl-base-1.0")
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_IMAGE_MODEL}"

_openai_img_client = None
_xai_img_client = None
_hf_session = None

def _get_image_client():
    """
    Returns (provider_name, client_like_object_or_session) or (None, None).
    - openai: returns OpenAI client
    - xai: returns OpenAI client pointed at x.ai base_url
    - huggingface: returns a requests.Session with auth header
    """
    global _openai_img_client, _xai_img_client, _hf_session

    if IMG_PROVIDER == "openai":
        from openai import OpenAI
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            return None, None
        if _openai_img_client is None:
            _openai_img_client = OpenAI(api_key=key)
        return "openai", _openai_img_client

    if IMG_PROVIDER == "xai":
        from openai import OpenAI
        key = os.getenv("XAI_API_KEY")
        if not key:
            return None, None
        if _xai_img_client is None:
            _xai_img_client = OpenAI(api_key=key, base_url="https://api.x.ai/v1")
        return "xai", _xai_img_client

    if IMG_PROVIDER == "huggingface":
        import requests
        token = os.getenv("HF_API_TOKEN")
        if not token:
            return None, None
        if _hf_session is None:
            s = requests.Session()
            s.headers.update({
                "Authorization": f"Bearer {token}",
                "Accept": "image/png",  # ask for raw PNG
            })
            _hf_session = s
        return "huggingface", _hf_session

    return None, None

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

# ================== Depth helpers ==================
def _length_for(detail_level: int, base: int, step: int = 120, cap: int = 1400) -> int:
    detail_level = max(1, min(3, int(detail_level)))
    return min(cap, base + (detail_level - 1) * step)

def _strictness_clause(strictness: float) -> str:
    strictness = max(0.0, min(1.0, float(strictness)))
    if strictness >= 0.8:
        return "Be rigorously historical; avoid legendary exaggerations unless attested in Iranian sources."
    if strictness >= 0.5:
        return "Be historically grounded; keep metaphors restrained and accurate to Iranian tradition."
    return "You may be mildly poetic, but keep references culturally Iranian and plausible."

def image_provider_info() -> dict:
    """
    Returns {'provider': 'huggingface'|'openai'|'xai', 'model': '<model_id>'}
    """
    if IMG_PROVIDER == "openai":
        return {"provider": "openai", "model": OPENAI_IMAGE_MODEL}
    if IMG_PROVIDER == "xai":
        return {"provider": "xai", "model": XAI_IMAGE_MODEL}
    if IMG_PROVIDER == "huggingface":
        return {"provider": "huggingface", "model": HF_IMAGE_MODEL}
    return {"provider": "unknown", "model": ""}


# ================== JSON preface scrubber ==================
def _extract_json(text: str) -> str:
    s = text.find("{"); e = text.rfind("}")
    return text[s:e+1] if (s != -1 and e != -1 and e > s) else text

# ================== Prompts & Generators ==================
FORBIDDEN_LINE = (
    "Forbidden terms: kshatra/kṣatra, dharma, karma, samsara, moksha, mantra, tantra, sutra, chakra, "
    "Veda/Vedic, atman, brahma/brahman/brahmin, Indra, Shiva, Vishnu, Ganesha, Lakshmi, Purusha, yuga, raja/rajah, Hindu/Hinduism."
)

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
  "appearance": "1–3 sentences on attire, notable features, and period-appropriate materials.",
  "dwelling": "1–3 sentences describing home/quarters typical for role and region.",
  "daily_routine": "3–5 bullet-like sentences describing a normal day.",
  "festival": "1–2 sentences on a seasonal rite or local festival they attend.",
  "short_story": "4–6 sentences: a small moment from their life, grounded and readable.",
  "backstory": "5–8 sentences: who they are, how they fit into the realm, and how traits map to their role.",
  "motto": "A short motto that fits the persona"
}}
""".strip()

def generate_parsverse_myth(
    name: str,
    region: str,
    style: str = "Epic",
    detail_level: int = 2,
    strictness: float = 0.6,
    themes: list[str] | None = None
) -> str:
    if not name or not region:
        raise ValueError("Both name and region are required.")
    region = _normalize_region(region)
    hint = REGION_HINTS.get(region, "")
    lex = ", ".join(REGION_LEXICON.get(region, []))
    translit_note = (
        "Prefer IRANIAN endonyms; if you include a Greek/Latin exonym, show it once in parentheses."
        if TRANSLIT_MODE == "modern" else
        "Use Old Persian/Avestan scholarly forms; avoid Greek/Latin exonyms."
    )
    themes_line = ", ".join(themes or [])
    depth_note = _strictness_clause(strictness)

    prompt = f"""
You are a cultural historian and storyteller of ancient Iran.
Compose a {style.lower()} mythic vignette about {name}, set in {region}. 
Make it personal and vivid, in 7–10 sentences, and include these labeled parts:

[Setting] 1–2 sentences anchoring time/place with region-appropriate details.
[Role] 1 sentence stating {name}'s station (tie to Iranian context).
[Conflict] 2–3 sentences—an ordeal or trial that fits the region.
[Turning Point] 1–2 sentences—choice, omen, or counsel.
[Resolution] 1–2 sentences—how it ends, with Iranian symbols/motifs.
[Moral] 1 line—concise, culturally fitting.

Context for accuracy: {hint}
Use a few region-appropriate motifs when relevant: {lex}
Optional themes to weave subtly: {themes_line if themes_line else "—"}

RULES:
- {translit_note}
- {depth_note}
- DO NOT use non-Iranian/Indic terms. {FORBIDDEN_LINE}
- Prefer clear modern English; gloss Persian terms once in brackets when first used.
- Return ONLY the prose with the labeled sections in order; no extra commentary.
""".strip()

    max_tokens = _length_for(detail_level, base=320, step=180, cap=1200)
    max_tries = 3
    last_text = ""

    for _ in range(max_tries):
        provider, client = _get_client()
        if provider == "openai":
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.85,
                max_tokens=max_tokens,
            )
            raw = resp.choices[0].message.content.strip()
        else:
            resp = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.85,
                max_tokens=max_tokens,
            )
            raw = resp.choices[0].message.content.strip()

        cleaned = prefer_persian_forms(sanitize_non_iranian(raw))
        last_text = cleaned
        if not contains_banned(cleaned):
            return cleaned

        prompt += (
            "\n\nREVISION: Your previous draft included forbidden Indic terms. "
            "Regenerate using ONLY Iranian terminology and keep section labels."
        )

    return last_text

def generate_parsverse_story(
    name: str,
    region: str,
    style: str = "Epic",
    detail_level: int = 3,
    strictness: float = 0.7,
    themes: list[str] | None = None
) -> str:
    if not name or not region:
        raise ValueError("Both name and region are required.")
    region = _normalize_region(region)
    hint = REGION_HINTS.get(region, "")
    lex = ", ".join(REGION_LEXICON.get(region, []))
    translit_note = (
        "Prefer IRANIAN endonyms; if you include a Greek/Latin exonym, show it once in parentheses."
        if TRANSLIT_MODE == "modern" else
        "Use Old Persian/Avestan scholarly forms; avoid Greek/Latin exonyms."
    )
    themes_line = ", ".join(themes or [])
    depth_note = _strictness_clause(strictness)

    prompt = f"""
You are a cultural historian and storyteller of ancient Iran.
Write a {style.lower()} **Epic Chronicle** about {name}, set in {region}.
Return 12–18 sentences across the labeled sections **exactly** as below:

[Cast] 2–4 short items naming key figures and their role/kinship (e.g., "Roxana — caravan scribe").
[Setting] 2–3 sentences grounding time/place with region details.
[Inciting Event] 2–3 sentences that set the story in motion.
[Rising Action] 3–4 sentences with obstacles and travel/ritual/work relevant to {region}.
[Climax] 2–3 sentences at the decisive moment; include **one** short line of dialogue in quotes.
[Aftermath] 2–3 sentences with consequences for the household/community.
[Closing Line] 1 sentence that lands as a proverb-like reflection.

Context for accuracy: {hint}
Use a few region-appropriate motifs when relevant: {lex}
Optional themes to weave subtly: {themes_line if themes_line else "—"}

RULES:
- {translit_note}
- {depth_note}
- DO NOT use non-Iranian/Indic terms. {FORBIDDEN_LINE}
- Prefer clear modern English; gloss Persian terms once in brackets when first used.
- Keep section labels **as shown** and in that order. No extra commentary.
""".strip()

    max_tokens = _length_for(detail_level, base=700, step=300, cap=1800)
    max_tries = 3
    last_text = ""

    for _ in range(max_tries):
        provider, client = _get_client()
        if provider == "openai":
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.88,
                max_tokens=max_tokens,
            )
            raw = resp.choices[0].message.content.strip()
        else:
            resp = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.88,
                max_tokens=max_tokens,
            )
            raw = resp.choices[0].message.content.strip()

        cleaned = prefer_persian_forms(sanitize_non_iranian(raw))
        last_text = cleaned
        if not contains_banned(cleaned):
            return cleaned

        prompt += (
            "\n\nREVISION: Your previous draft included forbidden Indic terms. "
            "Regenerate using ONLY Iranian terminology and keep the labeled sections."
        )

    return last_text

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
    last_data: dict | None = None
    last_concat = ""

    for _ in range(max_tries):
        # ---- Call LLM ----
        if PROVIDER == "openai":
            resp = openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1100,
            )
            raw = resp.choices[0].message.content.strip()
        elif PROVIDER == "groq":
            resp = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1100,
            )
            raw = resp.choices[0].message.content.strip()
        else:
            raise RuntimeError("No valid provider configured.")

        # ---- Strip code fences if present ----
        raw_clean = raw.strip()
        for fence in ("```json", "```"):
            if raw_clean.startswith(fence):
                raw_clean = raw_clean[len(fence):].strip()
        if raw_clean.endswith("```"):
            raw_clean = raw_clean[:-3].strip()

        # ---- Parse JSON (fallback: treat as backstory) ----
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
                "appearance": "",
                "dwelling": "",
                "daily_routine": "",
                "festival": "",
                "short_story": "",
                "backstory": raw_clean,
                "motto": ""
            }

        # ---- Normalize list-like fields that may arrive as arrays ----
        list_like_fields = [
            "daily_routine", "short_story", "backstory", "friends",
            "appearance", "dwelling", "festival"
        ]
        for k in list_like_fields:
            if isinstance(data.get(k), list):
                data[k] = "; ".join(str(x) for x in data[k])

        # ---- Clean/sanitize scalar string fields ----
        def clean_str(s: str) -> str:
            s = sanitize_non_iranian(s)
            s = prefer_persian_forms(s)
            return s

        for key in [
            "kingdom","locale","role","favorite_food","hobby","friends",
            "artifact","appearance","dwelling","daily_routine","festival",
            "short_story","backstory","motto"
        ]:
            if key in data and isinstance(data[key], str):
                data[key] = clean_str(data[key])

        # ---- Clean list fields (correct bug: check the value, not the key) ----
        for key in ["titles", "symbols"]:
            if key in data and isinstance(data[key], list):
                data[key] = [clean_str(str(x)) for x in data[key]]

        # ---- Build safe concat for banned-check (robust to types) ----
        def as_text(v):
            if isinstance(v, list):
                return " ".join(str(x) for x in v)
            if isinstance(v, dict):
                return json.dumps(v, ensure_ascii=False)
            return "" if v is None else str(v)

        last_data = data
        last_concat = " ".join([
            as_text(data.get("kingdom","")), as_text(data.get("locale","")), as_text(data.get("role","")),
            as_text(data.get("favorite_food","")), as_text(data.get("hobby","")), as_text(data.get("friends","")),
            as_text(data.get("titles", [])), as_text(data.get("symbols", [])),
            as_text(data.get("artifact","")), as_text(data.get("appearance","")), as_text(data.get("dwelling","")),
            as_text(data.get("daily_routine","")), as_text(data.get("festival","")),
            as_text(data.get("short_story","")), as_text(data.get("backstory","")), as_text(data.get("motto",""))
        ])

        # ---- If clean of banned terms, return ----
        if not contains_banned(last_concat):
            return data

        # ---- Tighten constraints and retry ----
        prompt += (
            "\n\nREVISION INSTRUCTIONS: Your previous draft included forbidden Indic terms. "
            "Regenerate STRICT JSON using ONLY Iranian terminology; strictly obey the forbidden list."
        )

    # Final fallback after retries
    return last_data or {
        "backstory": "Generation failed after retries. Please try again.",
        "short_story": ""
    }

# ================== Image prompt builders & generator ==================
def build_image_prompt_from_myth(myth_text: str, region: str) -> str:
    region = _normalize_region(region)
    hint = REGION_HINTS.get(region, "")
    return (
        "Create a single high-quality illustration inspired by ancient Iranian art, not anime. "
        "Composition: painterly, museum poster vibe, soft parchment tones with turquoise and gold accents. "
        "Subject is a scene from the following myth. Avoid anachronisms. Clothing, architecture, weapons "
        "should match Iranian context. No text in the image.\n\n"
        f"Region context: {hint}\n\n"
        f"Myth excerpt:\n{myth_text[:1200]}"
    )

def build_image_prompt_from_profile(profile: dict) -> str:
    region = profile.get("locale", "") or profile.get("kingdom", "")
    hint = ""
    for r, h in REGION_HINTS.items():
        if r in region:
            hint = h; break
    role = profile.get("role","")
    symbols = ", ".join(profile.get("symbols", [])[:3])
    appearance = profile.get("appearance","")
    return (
        "Create a portrait-style illustration inspired by ancient Iranian art. "
        "Subject: the persona described below. Warm parchment background, turquoise & gold accents. "
        "No text in the image. Historically grounded.\n\n"
        f"Region context: {hint}\n"
        f"Role: {role}\n"
        f"Symbols: {symbols}\n"
        f"Appearance notes: {appearance[:300]}"
    )

def generate_image_png_bytes(prompt: str, size: str = "1024x1024") -> bytes | None:
    """
    Returns PNG bytes or None. Chooses provider by IMG_PROVIDER env:
      - openai: gpt-image-1
      - xai: grok-2-image (OpenAI-compatible client)
      - huggingface: SDXL via Inference API
    """
    provider, client = _get_image_client()
    if provider is None or client is None:
        return None

    # Basic safety: nudge styles; remove text-in-image
    prompt_safe = (
        "Ancient Iranian-inspired illustration, respectful and historically grounded. "
        "No text in image. No real people. " + prompt
    )

    if provider == "openai":
        resp = client.images.generate(
            model=OPENAI_IMAGE_MODEL,
            prompt=prompt_safe,
            size=size,                     # e.g., "1024x1024"
            response_format="b64_json",
        )
        b64 = resp.data[0].b64_json
        return base64.b64decode(b64) if b64 else None

    if provider == "xai":
        # size may be ignored by backend; API is OpenAI-compatible
        resp = client.images.generate(
            model=XAI_IMAGE_MODEL,
            prompt=prompt_safe,
            response_format="b64_json",
        )
        b64 = resp.data[0].b64_json
        return base64.b64decode(b64) if b64 else None

    if provider == "huggingface":
        # Hugging Face Inference API – returns raw PNG bytes if Accept: image/png
        # You can pass generation params in JSON body. Wait for model so first call doesn’t 503.
        import requests, json as _json
        payload = {
            "inputs": prompt_safe,
            "options": {"wait_for_model": True},
            # Optional SDXL params:
            # "parameters": {
            #     "negative_prompt": "blurry, text, watermark, signature, low quality",
            #     "num_inference_steps": 30,
            #     "guidance_scale": 7.0,
            #     # "width": 1024, "height": 1024,   # many hosted pipelines ignore w/h
            # }
        }
        try:
            r: requests.Response = client.post(HF_API_URL, json=payload, timeout=60)
            ct = r.headers.get("Content-Type", "")
            if r.status_code == 200 and "image/" in ct:
                return r.content
            # If the model is still loading or an error occurred, HF returns JSON
            try:
                err = r.json()
                # Common messages: {"error": "...", "estimated_time": ...}
                # You can surface a friendlier message in the UI if you want.
                return None
            except Exception:
                return None
        except Exception:
            return None

    return None

# ---- Back-compat / typo aliases ----
def parseverse_myth(*args, **kwargs):
    return generate_parsverse_myth(*args, **kwargs)
def generate_parseverse_myth(*args, **kwargs):
    return generate_parsverse_myth(*args, **kwargs)

# ---- Local smoke test ----
if __name__ == "__main__":
    print("Provider:", PROVIDER, "| Translit mode:", TRANSLIT_MODE, "| IMG_PROVIDER:", IMG_PROVIDER)
    print("Has OpenAI image client:", _get_image_client()[0] is not None)
