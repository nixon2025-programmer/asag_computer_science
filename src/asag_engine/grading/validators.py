import json
from .schema import GradeResult

def _extract_json(raw_text: str) -> str:
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Model output did not contain a JSON object")
    return raw_text[start:end+1]

def parse_and_validate_grade(raw_text: str) -> GradeResult:
    obj = json.loads(_extract_json(raw_text))
    return GradeResult(**obj)

def clamp_grade(result: GradeResult) -> GradeResult:
    result.score_awarded = max(0.0, min(float(result.score_awarded), float(result.max_marks)))
    result.confidence = max(0.0, min(float(result.confidence), 1.0))
    return result