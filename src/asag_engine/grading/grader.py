from .prompt import build_grading_prompt
from .validators import parse_and_validate_grade, clamp_grade

def grade_submission(question, rubric_items, student_answer: str, llm_client, retry_on_fail: bool = True):
    system_text, user_text = build_grading_prompt(question, rubric_items, student_answer)

    raw = llm_client.generate(system_text, user_text)
    try:
        grade = parse_and_validate_grade(raw)
    except Exception:
        if not retry_on_fail:
            raise
        retry_system = system_text + "\n\nReturn ONLY valid JSON matching the schema. No extra words."
        raw2 = llm_client.generate(retry_system, user_text)
        grade = parse_and_validate_grade(raw2)
        raw = raw2

    grade = clamp_grade(grade)
    grade.max_marks = int(question.max_marks)

    rubric_marks = {r.id: float(r.marks) for r in rubric_items}
    total = 0.0
    fixed = []
    for mp in grade.mark_points_awarded:
        max_for_item = float(rubric_marks.get(mp.rubric_item_id, 0.0))
        mp.awarded = max(0.0, min(float(mp.awarded), max_for_item))
        fixed.append(mp)
        total += float(mp.awarded)

    grade.mark_points_awarded = fixed
    grade.score_awarded = max(0.0, min(total, float(question.max_marks)))
    return grade, raw