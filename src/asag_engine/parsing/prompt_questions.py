import json

SYSTEM_Q = """You are an exam question extractor.
You receive a chunk of a question paper (text only).
Extract ALL questions and sub-questions found in the chunk.

Output JSON ONLY with this schema:
{
  "subject": "...",
  "grade_level": "...",
  "topic": "... or null",
  "questions": [
    {"question_no": "string or null", "question_text": "string"}
  ]
}

Rules:
- Do not invent questions.
- Keep question_text clean and complete (as much as possible within the chunk).
- If question numbers are visible, preserve them (e.g., "1", "1(a)", "2(b)").
- If a question starts in this chunk but continues later, still include what you see.
- No markdown. JSON only.
"""

def build_questions_prompt(subject: str, grade_level: str, topic: str | None, paper_chunk: str) -> tuple[str, str]:
    user = {
        "metadata": {"subject": subject, "grade_level": grade_level, "topic": topic},
        "question_paper_chunk": paper_chunk,
        "required_schema": {
            "subject": "string",
            "grade_level": "string",
            "topic": "string|null",
            "questions": [{"question_no": "string|null", "question_text": "string"}]
        }
    }
    return SYSTEM_Q, json.dumps(user, ensure_ascii=False)