import os
import json
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session

from asag_engine.db.session import get_session
from asag_engine.db.models import Paper, Question, RubricItem
from asag_engine.utils import new_id, sha256_file
from asag_engine.grading.llm_client import build_llm_client
from asag_engine.parsing import parse_paper_pipeline

bp = Blueprint("papers", __name__)

def _ensure_dirs(base_dir: str):
    os.makedirs(os.path.join(base_dir, "papers"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "markschemes"), exist_ok=True)

def _paper_key(subject: str, grade_level: str, name: str | None) -> tuple[str, str, str]:
    return (subject.strip().lower(), grade_level.strip().lower(), (name or "").strip().lower())

@bp.post("/api/v1/papers/upload")
def upload_paper():
    """
    multipart/form-data:
    - subject (str) [required]
    - grade_level (str) [required]
    - topic (optional)
    - name (optional)
    - force_new (optional: "true" to bypass dedupe)
    - paper_file (pdf/docx) [required]
    - markscheme_file (pdf/docx) [required]
    """
    subject = (request.form.get("subject") or "").strip()
    grade_level = (request.form.get("grade_level") or "").strip()
    topic = (request.form.get("topic") or None)
    name = (request.form.get("name") or None)
    force_new = (request.form.get("force_new") or "false").lower() == "true"

    if not subject or not grade_level:
        return jsonify({"error": "subject and grade_level are required"}), 400

    paper_file = request.files.get("paper_file")
    markscheme_file = request.files.get("markscheme_file")
    if not paper_file or not markscheme_file:
        return jsonify({"error": "paper_file and markscheme_file are required"}), 400

    upload_dir = os.getenv("UPLOAD_DIR", "data/uploads")
    _ensure_dirs(upload_dir)

    temp_id = new_id("UPLOAD")
    paper_path = os.path.join(upload_dir, "papers", f"{temp_id}_{paper_file.filename}")
    ms_path = os.path.join(upload_dir, "markschemes", f"{temp_id}_{markscheme_file.filename}")

    paper_file.save(paper_path)
    markscheme_file.save(ms_path)

    paper_hash = sha256_file(paper_path)
    ms_hash = sha256_file(ms_path)

    session: Session = get_session()

    # DEDUPE: same hashes already exist => return existing (unless force_new)
    if not force_new:
        existing = (
            session.query(Paper)
            .filter(Paper.paper_sha256 == paper_hash, Paper.markscheme_sha256 == ms_hash)
            .first()
        )
        if existing:
            # cleanup newly uploaded duplicates (optional): keep for audit? We'll keep by default.
            qs = session.query(Question).filter(Question.paper_id == existing.id).all()
            return jsonify({
                "status": "duplicate",
                "paper_id": existing.id,
                "existing_revision": existing.revision,
                "created_questions": [{"id": q.id, "question_no": q.question_no, "max_marks": q.max_marks} for q in qs]
            }), 200

    # VERSIONING: if same (subject, grade, name) exists but different file hashes => new revision
    key = _paper_key(subject, grade_level, name)
    prior = (
        session.query(Paper)
        .filter(Paper.subject.ilike(subject), Paper.grade_level.ilike(grade_level))
        .filter(Paper.name == name)
        .order_by(Paper.revision.desc())
        .first()
    )
    next_revision = (prior.revision + 1) if prior else 1
    prior_id = prior.id if prior else None

    paper_id = new_id("PAPER")
    paper = Paper(
        id=paper_id,
        subject=subject,
        grade_level=grade_level,
        topic=topic,
        name=name,
        revision=next_revision,
        prior_paper_id=prior_id,
        paper_sha256=paper_hash,
        markscheme_sha256=ms_hash,
        paper_file_path=paper_path,
        markscheme_file_path=ms_path,
        status="uploaded",
    )
    session.add(paper)
    session.commit()

    # Parse (chunked) with MindNLP/Pangu
    llm = build_llm_client()
    try:
        aligned_questions, audit = parse_paper_pipeline(
            llm=llm,
            subject=subject,
            grade_level=grade_level,
            topic=topic,
            paper_path=paper.paper_file_path,
            markscheme_path=paper.markscheme_file_path
        )
        paper.parse_raw = json.dumps(audit, ensure_ascii=False)
        paper.parse_json = json.dumps([aq.model_dump() for aq in aligned_questions], ensure_ascii=False)
        paper.status = "parsed"
    except Exception as e:
        paper.status = "failed"
        paper.parse_error = str(e)
        session.commit()
        return jsonify({"error": "Failed to parse paper/markscheme", "details": str(e), "paper_id": paper.id}), 500

    # Write Questions + RubricItems
    created_questions = []
    for aq in aligned_questions:
        q = Question(
            id=new_id("Q"),
            paper_id=paper.id,
            subject=paper.subject,
            grade_level=paper.grade_level,
            topic=paper.topic,
            question_no=aq.question_no,
            question_text=aq.question_text,
            max_marks=int(aq.max_marks),
        )
        session.add(q)

        for ri in aq.rubric:
            r = RubricItem(
                id=new_id("RUB"),
                question_id=q.id,
                point_text=ri.point_text,
                marks=int(ri.marks),
                keywords_json="[]"
            )
            session.add(r)

        created_questions.append({"id": q.id, "question_no": q.question_no, "max_marks": q.max_marks})

    session.commit()

    return jsonify({
        "status": "parsed",
        "paper_id": paper.id,
        "revision": paper.revision,
        "prior_paper_id": paper.prior_paper_id,
        "created_questions": created_questions
    }), 201

@bp.get("/api/v1/papers")
def list_papers():
    session: Session = get_session()
    items = session.query(Paper).order_by(Paper.created_at.desc()).limit(200).all()
    return jsonify([
        {
            "id": p.id,
            "subject": p.subject,
            "grade_level": p.grade_level,
            "topic": p.topic,
            "name": p.name,
            "revision": p.revision,
            "status": p.status,
            "created_at": p.created_at.isoformat()
        }
        for p in items
    ]), 200

@bp.get("/api/v1/papers/<paper_id>")
def get_paper(paper_id: str):
    session: Session = get_session()
    p = session.query(Paper).filter(Paper.id == paper_id).first()
    if not p:
        return jsonify({"error": "Paper not found"}), 404

    qs = session.query(Question).filter(Question.paper_id == p.id).order_by(Question.created_at.asc()).all()
    return jsonify({
        "id": p.id,
        "subject": p.subject,
        "grade_level": p.grade_level,
        "topic": p.topic,
        "name": p.name,
        "revision": p.revision,
        "prior_paper_id": p.prior_paper_id,
        "status": p.status,
        "parse_error": p.parse_error,
        "questions": [
            {"id": q.id, "question_no": q.question_no, "max_marks": q.max_marks, "question_text": q.question_text}
            for q in qs
        ],
        "created_at": p.created_at.isoformat()
    }), 200