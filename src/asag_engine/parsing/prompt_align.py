import json

SYSTEM_ALIGN = """You are a marking-scheme aligner.

You receive:
- A batch of extracted questions (question_no + question_text)
- Markscheme text (one chunk)
- Metadata: subject, grade_level, topic

Task:
For EACH question in the batch:
- Determine max_marks (integer)
- Produce a rubric list with marking points and marks (integers)

Output JSON ONLY with schema:
{
  "aligned": [
    {
      "question_no": "string or null",
      "question_text": "string",
      "max_marks": integer,
      "rubric": [{"point_text":"string","marks": integer}]
    }
  ]
}

Rules:
- Rubric marks should sum <= max_marks (prefer equality if possible).
- Do not exceed max_marks.
- If you can't find marking details for a question in this markscheme chunk, still include the question with:
  - a conservative max_marks guess (e.g., 1–3), and rubric may be empty.
- JSON only, no markdown.
"""

def build_align_prompt(subject: str, grade_level: str, topic: str | None, questions_batch: list[dict], markscheme_chunk: str) -> tuple[str, str]:
    user = {
        "metadata": {"subject": subject, "grade_level": grade_level, "topic": topic},
        "questions": questions_batch,
        "markscheme_chunk": markscheme_chunk,
        "required_schema": {
            "aligned": [
                {"question_no":"string|null","question_text":"string","max_marks":"integer","rubric":[{"point_text":"string","marks":"integer"}]}
            ]
        }
    }
    return SYSTEM_ALIGN, json.dumps(user, ensure_ascii=False)