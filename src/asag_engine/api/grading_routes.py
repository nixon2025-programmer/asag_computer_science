from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session

from asag_engine.db.session import get_session
from asag_engine.db.models import Question, RubricItem, Submission
from asag_engine.grading.schema import GradeRequest
from asag_engine.grading.grader import grade_submission
from asag_engine.grading.llm_client import build_llm_client
from asag_engine.utils import new_id

bp = Blueprint("grading", __name__)
_llm = build_llm_client()

@bp.post("/api/v1/grade")
def grade():
    payload = GradeRequest(**request.get_json(force=True))
    session: Session = get_session()

    q = session.query(Question).filter(Question.id == payload.question_id).first()
    if not q:
        return jsonify({"error": "Question not found"}), 404

    rubric = session.query(RubricItem).filter(RubricItem.question_id == q.id).all()
    if not rubric:
        return jsonify({"error": "No rubric items found for this question"}), 400

    grade_result, raw = grade_submission(q, rubric, payload.student_answer, _llm, retry_on_fail=True)

    sub = Submission(
        id=new_id("SUB"),
        question_id=q.id,
        student_id=payload.student_id,
        student_answer=payload.student_answer,
        llm_raw=raw,
        model_grade_json=grade_result.model_dump_json(),
        final_grade_json=grade_result.model_dump_json(),
        score_awarded=float(grade_result.score_awarded),
    )
    session.add(sub)
    session.commit()

    out = grade_result.model_dump()
    out["submission_id"] = sub.id
    return jsonify(out), 200