from typing import List, Optional
from pydantic import BaseModel, Field, confloat, conint

class CreateRubricItem(BaseModel):
    point_text: str = Field(..., min_length=3)
    marks: conint(ge=0, le=50) = 1
    keywords: Optional[List[str]] = None

class CreateQuestionRequest(BaseModel):
    subject: str = Field(..., min_length=2)
    grade_level: str = Field(..., min_length=1)
    topic: Optional[str] = None
    question_no: Optional[str] = None
    question_text: str = Field(..., min_length=5)
    max_marks: conint(ge=1, le=300)
    rubric: List[CreateRubricItem] = Field(..., min_length=1)

class GradeRequest(BaseModel):
    question_id: str = Field(..., min_length=3)
    student_id: Optional[str] = None
    student_answer: str = Field(..., min_length=1)

class MarkPointAwarded(BaseModel):
    rubric_item_id: str
    awarded: confloat(ge=0)
    justification: str = Field(..., min_length=1)

class GradeResult(BaseModel):
    score_awarded: confloat(ge=0)
    max_marks: conint(ge=1)
    mark_points_awarded: List[MarkPointAwarded]
    missing_points: List[str]
    feedback_short: str
    confidence: confloat(ge=0, le=1)

class TeacherOverrideRequest(BaseModel):
    grade: GradeResult