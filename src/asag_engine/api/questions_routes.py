import json
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session

from asag_engine.db.session import get_session
from asag_engine.db.models import Question, RubricItem
from asag_engine.grading.schema import CreateQuestionRequest
from asag_engine.utils import new_id

bp = Blueprint("questions", __name__)

@bp.post("/api/v1/questions")
def create_question():
    payload = CreateQuestionRequest(**request.get_json(force=True))
    session: Session = get_session()

    q = Question(
        id=new_id("Q"),
        paper_id=None,
        subject=payload.subject,
        grade_level=payload.grade_level,
        topic=payload.topic,
        question_no=payload.question_no,
        question_text=payload.question_text,
        max_marks=int(payload.max_marks),
    )
    session.add(q)

    for item in payload.rubric:
        r = RubricItem(
            id=new_id("RUB"),
            question_id=q.id,
            point_text=item.point_text,
            marks=int(item.marks),
            keywords_json=json.dumps(item.keywords or [])
        )
        session.add(r)

    session.commit()
    return jsonify({"question_id": q.id}), 201

@bp.get("/api/v1/questions")
def list_questions():
    session: Session = get_session()
    items = session.query(Question).order_by(Question.created_at.desc()).limit(200).all()
    return jsonify([
        {
            "id": q.id,
            "paper_id": q.paper_id,
            "question_no": q.question_no,
            "subject": q.subject,
            "grade_level": q.grade_level,
            "topic": q.topic,
            "question_text": q.question_text,
            "max_marks": q.max_marks,
            "created_at": q.created_at.isoformat()
        }
        for q in items
    ]), 200

@bp.get("/api/v1/questions/<question_id>")
def get_question(question_id: str):
    session: Session = get_session()
    q = session.query(Question).filter(Question.id == question_id).first()
    if not q:
        return jsonify({"error": "Question not found"}), 404
    return jsonify({
        "id": q.id,
        "paper_id": q.paper_id,
        "question_no": q.question_no,
        "subject": q.subject,
        "grade_level": q.grade_level,
        "topic": q.topic,
        "question_text": q.question_text,
        "max_marks": q.max_marks,
        "created_at": q.created_at.isoformat()
    }), 200

@bp.get("/api/v1/questions/<question_id>/rubric")
def get_rubric(question_id: str):
    session: Session = get_session()
    items = session.query(RubricItem).filter(RubricItem.question_id == question_id).all()
    return jsonify([
        {"id": r.id, "question_id": r.question_id, "point_text": r.point_text, "marks": r.marks}
        for r in items
    ]), 200