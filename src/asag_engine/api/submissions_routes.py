from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session

from asag_engine.db.session import get_session
from asag_engine.db.models import Submission
from asag_engine.grading.schema import TeacherOverrideRequest

bp = Blueprint("submissions", __name__)

@bp.get("/api/v1/submissions")
def list_submissions():
    session: Session = get_session()
    items = session.query(Submission).order_by(Submission.created_at.desc()).limit(200).all()
    return jsonify([
        {
            "id": s.id,
            "question_id": s.question_id,
            "student_id": s.student_id,
            "score_awarded": s.score_awarded,
            "has_teacher_override": bool(s.teacher_grade_json),
            "created_at": s.created_at.isoformat()
        }
        for s in items
    ]), 200

@bp.get("/api/v1/submissions/<submission_id>")
def get_submission(submission_id: str):
    session: Session = get_session()
    s = session.query(Submission).filter(Submission.id == submission_id).first()
    if not s:
        return jsonify({"error": "Submission not found"}), 404
    return jsonify({
        "id": s.id,
        "question_id": s.question_id,
        "student_id": s.student_id,
        "student_answer": s.student_answer,
        "score_awarded": s.score_awarded,
        "llm_raw": s.llm_raw,
        "model_grade_json": s.model_grade_json,
        "teacher_grade_json": s.teacher_grade_json,
        "final_grade_json": s.final_grade_json,
        "created_at": s.created_at.isoformat()
    }), 200

@bp.patch("/api/v1/submissions/<submission_id>/override")
def override(submission_id: str):
    payload = TeacherOverrideRequest(**request.get_json(force=True))
    session: Session = get_session()

    s = session.query(Submission).filter(Submission.id == submission_id).first()
    if not s:
        return jsonify({"error": "Submission not found"}), 404

    teacher_json = payload.grade.model_dump_json()
    s.teacher_grade_json = teacher_json
    s.final_grade_json = teacher_json
    s.score_awarded = float(payload.grade.score_awarded)

    session.commit()
    return jsonify({"status": "ok", "submission_id": s.id}), 200