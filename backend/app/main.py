"""BrandCanon API. Run with:  uvicorn app.main:app --reload"""
import os, re, uuid
from datetime import datetime, date

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import llm
from .auth import current_user, require, verify_password, make_token
from .campaign import campaign_check
from .config import UPLOAD_DIR, CORS_ORIGINS
from .db import Base, engine, get_db, SessionLocal
from .engine import run_check
from .extract import extract_pdf, extract_docx, extract_text_file, image_colors
from .insights import build_insights
from .models import (User, Rule, Fact, Term, PaletteColor, Campaign, Content, Version, Finding,
                     Comment, AuditLog)
from .seed import seed, add_rules_from_text, next_rule_code

app = FastAPI(title="BrandCanon API", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)


def log(db: Session, user: User | None, action: str, target: str = "", detail: str = ""):
    db.add(AuditLog(user_id=user.id if user else None, action=action, target=target, detail=detail))


# ---------------------------------------------------------------- auth
class LoginIn(BaseModel):
    email: str
    password: str


@app.post("/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.strip().lower()).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Wrong email or password")
    return {"token": make_token(user), "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role}}


@app.get("/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}


@app.get("/health")
def health():
    return {"ok": True, "ai_enabled": llm.ai_enabled(), "model": llm.LLM_MODEL if llm.ai_enabled() else None}


@app.get("/ai/test")
def ai_test(user: User = Depends(current_user)):
    """Checks the AI key and model names. Open it from /docs after logging in."""
    return llm.self_test()


# ---------------------------------------------------------------- brand knowledge
def rule_out(r: Rule):
    return {"id": r.id, "code": r.code, "category": r.category, "text": r.text, "severity": r.severity,
            "version": r.version, "source": r.source}


class RuleIn(BaseModel):
    category: str
    text: str
    severity: str = "major"


@app.get("/brand/rules")
def list_rules(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [rule_out(r) for r in db.query(Rule).filter(Rule.active == True).order_by(Rule.code)]  # noqa: E712


@app.post("/brand/rules")
def add_rule(body: RuleIn, db: Session = Depends(get_db), user: User = Depends(require("admin"))):
    r = Rule(code=next_rule_code(db, body.category), category=body.category, text=body.text.strip(), severity=body.severity)
    db.add(r)
    log(db, user, "rule.create", r.code, body.text)
    db.commit()
    return rule_out(r)


@app.put("/brand/rules/{rule_id}")
def edit_rule(rule_id: int, body: RuleIn, db: Session = Depends(get_db), user: User = Depends(require("admin"))):
    r = db.get(Rule, rule_id)
    if not r:
        raise HTTPException(404, "Rule not found")
    if body.text.strip() != r.text:
        r.version += 1          # findings keep the version they were checked against
        r.embedding = None      # re-embed on next check
    r.text, r.category, r.severity = body.text.strip(), body.category, body.severity
    log(db, user, "rule.update", r.code, f"v{r.version}: {r.text}")
    db.commit()
    return rule_out(r)


@app.delete("/brand/rules/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db), user: User = Depends(require("admin"))):
    r = db.get(Rule, rule_id)
    if r:
        r.active = False
        log(db, user, "rule.retire", r.code)
        db.commit()
    return {"ok": True}


def save_upload(file: UploadFile) -> tuple[str, str]:
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", file.filename or "file")
    path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex[:10]}_{safe}")
    with open(path, "wb") as f:
        f.write(file.file.read())
    return path, ext


def read_document(path: str, ext: str):
    if ext == "pdf":
        return extract_pdf(path)
    if ext == "docx":
        return extract_docx(path)
    if ext in ("txt", "md"):
        return extract_text_file(path)
    raise HTTPException(400, "Unsupported file type. Use PDF, DOCX, TXT, PNG or JPG.")


@app.post("/brand/rules/upload")
def upload_guidelines(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(require("admin"))):
    path, ext = save_upload(file)
    text, _ = read_document(path, ext)
    n = add_rules_from_text(db, text, file.filename or "upload")
    log(db, user, "guidelines.upload", file.filename or "", f"{n} rules added")
    db.commit()
    return {"rules_added": n}


class FactIn(BaseModel):
    label: str
    value: str
    value_type: str
    keywords: str
    valid_until: date | None = None


def fact_out(f: Fact):
    return {"id": f.id, "code": f.code, "label": f.label, "value": f.value, "value_type": f.value_type,
            "keywords": f.keywords, "valid_until": f.valid_until.isoformat() if f.valid_until else None,
            "expired": bool(f.valid_until and f.valid_until < date.today()), "version": f.version}


@app.get("/brand/facts")
def list_facts(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [fact_out(f) for f in db.query(Fact).order_by(Fact.code)]


@app.post("/brand/facts")
def add_fact(body: FactIn, db: Session = Depends(get_db), user: User = Depends(require("admin"))):
    n = db.query(Fact).count() + 1
    while db.query(Fact).filter(Fact.code == f"F-{n:02d}").first():
        n += 1
    f = Fact(code=f"F-{n:02d}", **body.model_dump())
    db.add(f)
    log(db, user, "fact.create", f.code, f"{body.label} = {body.value}")
    db.commit()
    return fact_out(f)


@app.put("/brand/facts/{fact_id}")
def edit_fact(fact_id: int, body: FactIn, db: Session = Depends(get_db), user: User = Depends(require("admin"))):
    f = db.get(Fact, fact_id)
    if not f:
        raise HTTPException(404, "Fact not found")
    for k, v in body.model_dump().items():
        setattr(f, k, v)
    f.version += 1
    log(db, user, "fact.update", f.code, f"{body.label} = {body.value}")
    db.commit()
    return fact_out(f)


@app.delete("/brand/facts/{fact_id}")
def delete_fact(fact_id: int, db: Session = Depends(get_db), user: User = Depends(require("admin"))):
    f = db.get(Fact, fact_id)
    if f:
        log(db, user, "fact.delete", f.code)
        db.delete(f)
        db.commit()
    return {"ok": True}


class TermIn(BaseModel):
    preferred: str = ""
    variants: str
    note: str = ""
    severity: str = "major"


def term_out(t: Term):
    return {"id": t.id, "code": t.code, "preferred": t.preferred, "variants": t.variants, "note": t.note, "severity": t.severity}


@app.get("/brand/terms")
def list_terms(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [term_out(t) for t in db.query(Term).order_by(Term.code)]


@app.post("/brand/terms")
def add_term(body: TermIn, db: Session = Depends(get_db), user: User = Depends(require("admin"))):
    n = db.query(Term).count() + 1
    while db.query(Term).filter(Term.code == f"T-{n:02d}").first():
        n += 1
    t = Term(code=f"T-{n:02d}", **body.model_dump())
    db.add(t)
    log(db, user, "term.create", t.code, body.variants)
    db.commit()
    return term_out(t)


@app.delete("/brand/terms/{term_id}")
def delete_term(term_id: int, db: Session = Depends(get_db), user: User = Depends(require("admin"))):
    t = db.get(Term, term_id)
    if t:
        log(db, user, "term.delete", t.code)
        db.delete(t)
        db.commit()
    return {"ok": True}


class ColorIn(BaseModel):
    name: str
    hex: str


@app.get("/brand/palette")
def list_palette(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [{"id": p.id, "name": p.name, "hex": p.hex} for p in db.query(PaletteColor)]


@app.post("/brand/palette")
def add_color(body: ColorIn, db: Session = Depends(get_db), user: User = Depends(require("admin"))):
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", body.hex):
        raise HTTPException(400, "Colour must be a hex code like #E2703A")
    p = PaletteColor(name=body.name, hex=body.hex.upper())
    db.add(p)
    log(db, user, "palette.add", body.hex)
    db.commit()
    return {"id": p.id, "name": p.name, "hex": p.hex}


@app.delete("/brand/palette/{color_id}")
def delete_color(color_id: int, db: Session = Depends(get_db), user: User = Depends(require("admin"))):
    p = db.get(PaletteColor, color_id)
    if p:
        db.delete(p)
        db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- campaigns
@app.get("/campaigns")
def list_campaigns(db: Session = Depends(get_db), user: User = Depends(current_user)):
    out = []
    for c in db.query(Campaign).order_by(Campaign.name):
        out.append({"id": c.id, "name": c.name, "items": db.query(Content).filter(Content.campaign_id == c.id).count()})
    return out


@app.get("/campaigns/{campaign_id}/check")
def check_campaign(campaign_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = db.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(404, "Campaign not found")
    return {"campaign": {"id": c.id, "name": c.name}, **campaign_check(db, campaign_id)}


# ---------------------------------------------------------------- content
def finding_out(f: Finding):
    return {"id": f.id, "lane": f.lane, "category": f.category, "severity": f.severity, "quote": f.quote,
            "start": f.start, "end": f.end, "rule_code": f.rule_code, "rule_version": f.rule_version,
            "rule_text": f.rule_text, "reason": f.reason, "suggestion": f.suggestion,
            "replacement": f.replacement, "status": f.status, "resolution_note": f.resolution_note}


def content_summary(db: Session, c: Content):
    fs = db.query(Finding).filter(Finding.content_id == c.id, Finding.version_number == c.current_version).all()
    open_ = [f for f in fs if f.status == "open"]
    return {"id": c.id, "title": c.title, "kind": c.kind, "status": c.status, "version": c.current_version,
            "campaign": c.campaign.name if c.campaign else None, "campaign_id": c.campaign_id,
            "creator": c.creator.name, "creator_id": c.creator_id,
            "open_findings": len(open_), "blocking_open": len([f for f in open_ if f.severity == "blocking"]),
            "updated_at": c.updated_at.isoformat()}


def get_content(db: Session, content_id: int, user: User) -> Content:
    c = db.get(Content, content_id)
    if not c:
        raise HTTPException(404, "Content not found")
    if user.role == "creator" and c.creator_id != user.id:
        raise HTTPException(403, "You can only open your own content")
    return c


def current_version(db: Session, c: Content) -> Version:
    return db.query(Version).filter(Version.content_id == c.id, Version.number == c.current_version).first()


def build_version(content_kind: str | None, text: str, file: UploadFile | None, alt_text: str, image_text: str):
    """Returns (kind, text, file_path, colors, meta) for a new version."""
    if file is not None and file.filename:
        path, ext = save_upload(file)
        if ext in ("png", "jpg", "jpeg", "webp"):
            colors = image_colors(path)
            extracted = image_text.strip() or llm.read_image_text(path)
            meta = {"alt_text": alt_text.strip(), "text_source": "typed by creator" if image_text.strip() else
                    ("vision model" if extracted else "none")}
            return "image", extracted, path, colors, meta
        doc_text, meta = read_document(path, ext)
        return ("text" if ext in ("txt", "md") else ext), doc_text, path, None, meta
    if not text.strip():
        raise HTTPException(400, "Add some text or upload a file")
    return "text", text.strip(), None, None, {}


@app.get("/contents")
def list_contents(db: Session = Depends(get_db), user: User = Depends(current_user)):
    q = db.query(Content)
    if user.role == "creator":
        q = q.filter(Content.creator_id == user.id)
    return [content_summary(db, c) for c in q.order_by(Content.updated_at.desc())]


@app.post("/contents")
def create_content(title: str = Form(...), text: str = Form(""), campaign_id: int | None = Form(None),
                   campaign_name: str = Form(""), alt_text: str = Form(""), image_text: str = Form(""),
                   file: UploadFile | None = File(None),
                   db: Session = Depends(get_db), user: User = Depends(require("creator", "admin"))):
    kind, body, path, colors, meta = build_version(None, text, file, alt_text, image_text)
    if campaign_name.strip():
        camp = db.query(Campaign).filter(Campaign.name == campaign_name.strip()).first()
        if not camp:
            camp = Campaign(name=campaign_name.strip())
            db.add(camp)
            db.flush()
        campaign_id = camp.id
    c = Content(title=title.strip(), kind=kind, campaign_id=campaign_id, creator_id=user.id)
    db.add(c)
    db.flush()
    v = Version(content_id=c.id, number=1, text=body, file_path=path, colors=colors, meta=meta, note="First upload")
    db.add(v)
    log(db, user, "content.create", f"content:{c.id}", title)
    db.commit()
    run_check(db, c, v)
    return {"id": c.id}


@app.get("/contents/{content_id}")
def content_detail(content_id: int, version: int | None = None, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = get_content(db, content_id, user)
    number = version or c.current_version
    v = db.query(Version).filter(Version.content_id == c.id, Version.number == number).first()
    if not v:
        raise HTTPException(404, "Version not found")
    findings = db.query(Finding).filter(Finding.content_id == c.id, Finding.version_number == number).order_by(Finding.id).all()
    versions = db.query(Version).filter(Version.content_id == c.id).order_by(Version.number.desc()).all()
    comments = db.query(Comment).filter(Comment.content_id == c.id).order_by(Comment.id).all()
    return {
        **content_summary(db, c),
        "viewing_version": number,
        "text": v.text, "has_file": bool(v.file_path), "colors": v.colors, "meta": v.meta or {},
        "findings": [finding_out(f) for f in findings],
        "versions": [{"number": x.number, "note": x.note, "created_at": x.created_at.isoformat()} for x in versions],
        "comments": [{"id": m.id, "user": m.user.name, "role": m.user.role, "text": m.text,
                      "created_at": m.created_at.isoformat()} for m in comments],
        "ai_enabled": llm.ai_enabled(),
    }


@app.get("/contents/{content_id}/file")
def content_file(content_id: int, version: int | None = None, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = get_content(db, content_id, user)
    v = db.query(Version).filter(Version.content_id == c.id, Version.number == (version or c.current_version)).first()
    if not v or not v.file_path or not os.path.exists(v.file_path):
        raise HTTPException(404, "No file for this version")
    return FileResponse(v.file_path)


def add_version(db: Session, c: Content, user: User, text: str, path, colors, meta, note: str):
    c.current_version += 1
    c.status = "draft"
    c.updated_at = datetime.utcnow()
    v = Version(content_id=c.id, number=c.current_version, text=text, file_path=path, colors=colors, meta=meta, note=note)
    db.add(v)
    log(db, user, "content.new_version", f"content:{c.id}", f"v{c.current_version}: {note}")
    db.commit()
    run_check(db, c, v)
    return v


@app.post("/contents/{content_id}/versions")
def new_version(content_id: int, text: str = Form(""), alt_text: str = Form(""), image_text: str = Form(""),
                note: str = Form("Edited by creator"), file: UploadFile | None = File(None),
                db: Session = Depends(get_db), user: User = Depends(require("creator", "admin"))):
    c = get_content(db, content_id, user)
    old = current_version(db, c)
    if file is not None and file.filename:
        kind, body, path, colors, meta = build_version(c.kind, text, file, alt_text, image_text)
        c.kind = kind
    else:
        if c.kind == "image":
            # same image, creator updated the typed text / alt text
            meta = dict(old.meta or {})
            meta.pop("check", None)
            if alt_text.strip():
                meta["alt_text"] = alt_text.strip()
            body, path, colors = (text.strip() or old.text), old.file_path, old.colors
        else:
            if not text.strip():
                raise HTTPException(400, "Text is empty")
            body, path, colors = text.strip(), old.file_path, None
            meta = {k: v for k, v in (old.meta or {}).items() if k != "check"}
    add_version(db, c, user, body, path, colors, meta, note)
    return {"version": c.current_version}


@app.post("/contents/{content_id}/apply-fixes")
def apply_fixes(content_id: int, db: Session = Depends(get_db), user: User = Depends(require("creator", "admin"))):
    """Apply every accepted suggestion to the text and save it as a new version."""
    c = get_content(db, content_id, user)
    if c.kind == "image":
        raise HTTPException(400, "Fixes cannot be applied to an image automatically. Upload a corrected image as a new version.")
    v = current_version(db, c)
    accepted = [f for f in db.query(Finding).filter(Finding.content_id == c.id, Finding.version_number == v.number,
                                                    Finding.status == "accepted").all()
                if f.replacement is not None and f.start is not None]
    if not accepted:
        raise HTTPException(400, "No accepted suggestions to apply. Accept at least one suggestion first.")
    text, last_start, applied = v.text, None, 0
    for f in sorted(accepted, key=lambda x: -x.start):       # work backwards so positions stay valid
        if last_start is not None and f.end > last_start:     # overlapping edits: skip the earlier one
            continue
        if text[f.start:f.end] != f.quote:
            continue
        text = text[:f.start] + f.replacement + text[f.end:]
        last_start, applied = f.start, applied + 1
    meta = {k: val for k, val in (v.meta or {}).items() if k != "check"}
    add_version(db, c, user, text, v.file_path, None, meta, f"Applied {applied} accepted suggestion(s)")
    return {"version": c.current_version, "applied": applied}


@app.post("/contents/{content_id}/check")
def recheck(content_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = get_content(db, content_id, user)
    stats = run_check(db, c, current_version(db, c))
    log(db, user, "content.recheck", f"content:{c.id}")
    db.commit()
    return stats


class FindingPatch(BaseModel):
    status: str                 # accepted | dismissed | open
    note: str = ""
    replacement: str | None = None   # creator may edit the suggested fix


@app.patch("/findings/{finding_id}")
def update_finding(finding_id: int, body: FindingPatch, db: Session = Depends(get_db), user: User = Depends(current_user)):
    f = db.get(Finding, finding_id)
    if not f:
        raise HTTPException(404, "Finding not found")
    c = get_content(db, f.content_id, user)
    if body.status not in ("accepted", "dismissed", "open"):
        raise HTTPException(400, "Unknown status")
    if body.status == "dismissed":
        if f.severity == "blocking":
            raise HTTPException(400, "Blocking issues cannot be dismissed. Fix them, or a reviewer can override with a reason at approval.")
        if len(body.note.strip()) < 5:
            raise HTTPException(400, "Please give a short reason for dismissing this finding.")
    if body.replacement is not None and body.replacement.strip():
        f.replacement = body.replacement.strip()
    f.status, f.resolution_note, f.resolved_by = body.status, body.note.strip(), user.id
    log(db, user, f"finding.{body.status}", f"content:{c.id}", f"{f.rule_code} \"{f.quote[:60]}\" {body.note}")
    db.commit()
    return finding_out(f)


@app.post("/contents/{content_id}/submit")
def submit(content_id: int, db: Session = Depends(get_db), user: User = Depends(require("creator", "admin"))):
    c = get_content(db, content_id, user)
    if c.status not in ("draft", "changes_requested"):
        raise HTTPException(400, f"Content is already {c.status.replace('_', ' ')}")
    c.status, c.updated_at = "in_review", datetime.utcnow()
    log(db, user, "content.submit", f"content:{c.id}", f"v{c.current_version}")
    db.commit()
    return {"status": c.status}


class ReviewIn(BaseModel):
    decision: str               # approve | request_changes
    comment: str = ""
    override_reason: str = ""


@app.post("/contents/{content_id}/review")
def review(content_id: int, body: ReviewIn, db: Session = Depends(get_db), user: User = Depends(require("reviewer", "admin"))):
    c = get_content(db, content_id, user)
    if c.status != "in_review":
        raise HTTPException(400, "This content is not waiting for review")
    if body.decision == "approve":
        blocking = db.query(Finding).filter(Finding.content_id == c.id, Finding.version_number == c.current_version,
                                            Finding.severity == "blocking", Finding.status == "open").all()
        if blocking:
            if len(body.override_reason.strip()) < 10:
                raise HTTPException(409, f"{len(blocking)} blocking issue(s) are still open. Request changes, or give a written override reason (at least 10 characters).")
            for f in blocking:
                f.status, f.resolution_note, f.resolved_by = "overridden", body.override_reason.strip(), user.id
            log(db, user, "review.override", f"content:{c.id}", f"{len(blocking)} blocking issue(s): {body.override_reason.strip()}")
        c.status = "approved"
        log(db, user, "review.approve", f"content:{c.id}", f"v{c.current_version}")
    elif body.decision == "request_changes":
        if len(body.comment.strip()) < 5:
            raise HTTPException(400, "Tell the creator what to change")
        c.status = "changes_requested"
        log(db, user, "review.request_changes", f"content:{c.id}", body.comment.strip())
    else:
        raise HTTPException(400, "Unknown decision")
    if body.comment.strip():
        db.add(Comment(content_id=c.id, user_id=user.id, text=body.comment.strip()))
    c.updated_at = datetime.utcnow()
    db.commit()
    return {"status": c.status}


class CommentIn(BaseModel):
    text: str


@app.post("/contents/{content_id}/comments")
def add_comment(content_id: int, body: CommentIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = get_content(db, content_id, user)
    if not body.text.strip():
        raise HTTPException(400, "Comment is empty")
    db.add(Comment(content_id=c.id, user_id=user.id, text=body.text.strip()))
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- insights & audit
@app.get("/insights")
def insights(db: Session = Depends(get_db), user: User = Depends(require("admin", "reviewer"))):
    return build_insights(db)


@app.get("/audit")
def audit(db: Session = Depends(get_db), user: User = Depends(require("admin", "reviewer"))):
    rows = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(100).all()
    return [{"id": a.id, "user": a.user.name if a.user else "system", "action": a.action, "target": a.target,
             "detail": a.detail, "created_at": a.created_at.isoformat()} for a in rows]
