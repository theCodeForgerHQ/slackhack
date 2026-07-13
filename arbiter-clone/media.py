"""File/image support for Verdict (Step 5 #4).

Given a Slack file (screenshot, PDF, Word, text), extract the single checkable claim:
- images  -> a vision model reads the claim out of the picture
- PDF/Word/text -> extract text, then condense to the main claim
Requires the bot's `files:read` scope to download the file.
"""
import os
import io
import base64
import httpx
from openai import OpenAI

from llm import _PROVIDERS, _pm, _chat, SYNTH

VISION = _pm(os.environ.get("VERDICT_VISION", "nvidia:nvidia/nemotron-nano-12b-v2-vl"))
_vbase, _vkey = _PROVIDERS[VISION[0]]
_vclient = OpenAI(base_url=_vbase, api_key=os.environ[_vkey])

_CONDENSE = ("Extract the single most important checkable factual claim from this text as one "
             "concise sentence. If there is no checkable factual claim, reply exactly: NONE.")


def _download(f: dict) -> bytes:
    url = f.get("url_private_download") or f.get("url_private")
    r = httpx.get(url, headers={"Authorization": f"Bearer {os.environ['SLACK_BOT_TOKEN']}"},
                  follow_redirects=True, timeout=30)
    r.raise_for_status()
    return r.content


def _claim_from_image(raw: bytes, mimetype: str) -> str:
    dataurl = f"data:{mimetype};base64,{base64.b64encode(raw).decode()}"
    r = _vclient.chat.completions.create(
        model=VISION[1], max_tokens=200,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": "Read this image. State the single main factual claim it "
             "makes as one concise sentence I can fact-check. If there is no checkable factual "
             "claim, reply exactly: NONE."},
            {"type": "image_url", "image_url": {"url": dataurl}}]}],
    )
    return (r.choices[0].message.content or "").strip()


def _text_from_pdf(raw: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(raw))
    return "\n".join((p.extract_text() or "") for p in reader.pages)[:6000]


def _text_from_docx(raw: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(raw))
    return "\n".join(p.text for p in doc.paragraphs)[:6000]


def _transcribe(raw: bytes, mimetype: str) -> str:
    """Speech-to-text via Deepgram's pre-recorded API (batch — Slack gives us a file)."""
    r = httpx.post(
        "https://api.deepgram.com/v1/listen?smart_format=true&punctuate=true&detect_language=true",
        headers={"Authorization": f"Token {os.environ['DEEPGRAM_API_KEY']}",
                 "Content-Type": mimetype or "audio/mpeg"},
        content=raw, timeout=90,
    )
    d = r.json()
    return d["results"]["channels"][0]["alternatives"][0]["transcript"]


def _claim_from_text(text: str) -> str:
    if not text.strip():
        return "NONE"
    return _chat(SYNTH[0], SYNTH[1], _CONDENSE, text).strip()


def extract_text(f: dict) -> str:
    """Return the full text of a document (for whole-document fact-checking)."""
    name = (f.get("name") or "").lower()
    mt = (f.get("mimetype") or "").lower()
    raw = _download(f)
    if mt == "application/pdf" or name.endswith(".pdf"):
        return _text_from_pdf(raw)
    if "word" in mt or name.endswith(".docx"):
        return _text_from_docx(raw)
    try:
        return raw.decode("utf-8", "ignore")
    except Exception:
        return ""


def claim_from_file(f: dict) -> str:
    """Return a one-sentence checkable claim from a Slack file, or 'NONE'."""
    name = (f.get("name") or "").lower()
    mt = (f.get("mimetype") or "").lower()
    raw = _download(f)
    if (mt.startswith("audio/") or mt.startswith("video/")
            or name.endswith((".mp3", ".m4a", ".wav", ".ogg", ".webm", ".mp4", ".aac"))):
        return _claim_from_text(_transcribe(raw, mt or "audio/mpeg"))
    if mt.startswith("image/"):
        return _claim_from_image(raw, mt)
    if mt == "application/pdf" or name.endswith(".pdf"):
        return _claim_from_text(_text_from_pdf(raw))
    if "word" in mt or name.endswith(".docx"):
        return _claim_from_text(_text_from_docx(raw))
    try:
        return _claim_from_text(raw.decode("utf-8", "ignore"))
    except Exception:
        return "NONE"
