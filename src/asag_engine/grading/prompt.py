import json

SYSTEM_INSTRUCTIONS = """You are an Automated Short Answer Grader (ASAG) for Computer Science.
You MUST grade strictly using the rubric items provided.

Rules:
- Award marks ONLY if the student's answer matches the rubric point.
- For each rubric item, awarded must be between 0 and that item's marks.
- Never exceed max_marks total.
- If unsure, award 0 for that rubric item.
- Output JSON ONLY that matches the required schema.
- No extra text, no markdown, no explanations outside JSON.
"""

def build_grading_prompt(question, rubric_items, student_answer: str):
    rubric_payload = [{"rubric_item_id": r.id, "marks": r.marks, "point_text": r.point_text} for r in rubric_items]
    user_obj = {
        "subject": question.subject,
        "grade_level": question.grade_level,
        "topic": question.topic,
        "max_marks": question.max_marks,
        "question_text": question.question_text,
        "rubric": rubric_payload,
        "student_answer": student_answer,
        "required_output_schema": {
            "score_awarded": "number",
            "max_marks": "integer",
            "mark_points_awarded": [{"rubric_item_id": "string", "awarded": "number", "justification": "string"}],
            "missing_points": ["string"],
            "feedback_short": "string",
            "confidence": "number in [0,1]"
        }
    }
    return SYSTEM_INSTRUCTIONS, json.dumps(user_obj, ensure_ascii=False)