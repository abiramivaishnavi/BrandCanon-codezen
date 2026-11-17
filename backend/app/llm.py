"""Thin wrapper around an OpenAI-compatible API (Gemini by default).

Everything degrades gracefully: with no API key the app uses a local
bag-of-words embedding and skips the AI (Advisory) lane."""
import base64, hashlib, json, math, os, re, time

from .config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, EMBED_MODEL

_client = None


def ai_enabled() -> bool:
    return bool(LLM_API_KEY)


def client():
    global _client
    if _client is None and ai_enabled():
        from openai import OpenAI
        _client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, timeout=60, max_retries=2)
    return _client


# ---------- embeddings ----------
def _local_embed(text: str, dim: int = 384):
    """Hashing bag-of-words vector. Not as good as a real embedding model, but
    deterministic, free and good enough to rank a few dozen rules."""
    vec = [0.0] * dim
    words = re.findall(r"[a-z']+", text.lower())
    for w in words + [a + " " + b for a, b in zip(words, words[1:])]:
        h = int(hashlib.md5(w.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def embed_method() -> str:
    return f"api:{EMBED_MODEL}" if ai_enabled() else "local-bow"


def embed(texts: list[str]):
    """Returns (method, vectors). Falls back to local vectors if the API fails."""
    if ai_enabled():
        try:
            res = client().embeddings.create(model=EMBED_MODEL, input=texts)
            return f"api:{EMBED_MODEL}", [d.embedding for d in res.data]
        except Exception as e:  # network / quota / model name problems
            print("[embed] API failed, using local embeddings:", e)
    return "local-bow", [_local_embed(t) for t in texts]


def cosine(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


# ---------- chat ----------
def _parse_json(raw: str):
    try:
        return json.loads(raw)
    except Exception:
        m = re.search(r"\{.*\}", raw or "", re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


def chat_json(system: str, user: str, image_path: str | None = None):
    """Ask the model for a JSON object. Returns a dict, or None on any failure."""
    if not ai_enabled():
        return None
    content = [{"type": "text", "text": user}]
    if image_path:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        ext = image_path.rsplit(".", 1)[-1].lower().replace("jpg", "jpeg")
        content.append({"type": "image_url", "image_url": {"url": f"data:image/{ext};base64,{b64}"}})
    messages = [{"role": "system", "content": system}, {"role": "user", "content": content if image_path else user}]
        # Try the main model first; if it is busy or unavailable, try the fallbacks in order.
    fallbacks = [m.strip() for m in os.getenv("LLM_FALLBACK_MODELS", "").split(",") if m.strip()]
    for model in [LLM_MODEL] + fallbacks:
        for attempt in range(2):
            try:
                # 2nd attempt drops the optional parameters, in case the model rejects them
                extra = {"temperature": 0, "response_format": {"type": "json_object"}} if attempt == 0 else {}
                res = client().chat.completions.create(model=model, messages=messages, **extra)
                data = _parse_json(res.choices[0].message.content)
                if isinstance(data, dict):
                    return data
            except Exception as e:
                print(f"[chat_json] {model} attempt {attempt + 1} failed:", str(e)[:200])
                time.sleep(1.5)
    return None


def read_image_text(image_path: str) -> str:
    """Use the vision model as OCR for posters and social creatives."""
    data = chat_json(
        "You read marketing images. Return JSON only.",
        'Transcribe ALL text visible in this image exactly as written, top to bottom, one line per text block. '
        'Return {"text": "..."} . Do not describe the image and do not correct any mistakes.',
        image_path=image_path,
    )
    return (data or {}).get("text", "").strip() if data else ""


def self_test() -> dict:
    """Used by GET /ai/test so the team can check the key and model names quickly."""
    if not ai_enabled():
        return {"ai_enabled": False, "message": "LLM_API_KEY is not set. The app runs with the Verified lane only."}
    out = {"ai_enabled": True, "model": LLM_MODEL, "embed_model": EMBED_MODEL}
    try:
        res = client().chat.completions.create(model=LLM_MODEL, messages=[{"role": "user", "content": 'Reply with the JSON {"ok": true}'}])
        out["chat"] = "ok: " + (res.choices[0].message.content or "")[:60]
    except Exception as e:
        out["chat"] = "FAILED: " + str(e)[:300]
    try:
        res = client().embeddings.create(model=EMBED_MODEL, input=["hello"])
        out["embeddings"] = f"ok: {len(res.data[0].embedding)} dimensions"
    except Exception as e:
        out["embeddings"] = "FAILED (local fallback will be used): " + str(e)[:300]
    return out
