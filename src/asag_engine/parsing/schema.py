from typing import List, Optional
from pydantic import BaseModel, Field, conint

class ParsedQuestionLite(BaseModel):
    question_no: Optional[str] = None
    question_text: str = Field(..., min_length=5)

class ParsedQuestionsLite(BaseModel):
    subject: str = Field(..., min_length=2)
    grade_level: str = Field(..., min_length=1)
    topic: Optional[str] = None
    questions: List[ParsedQuestionLite] = Field(..., min_length=1)

class ParsedRubricItem(BaseModel):
    point_text: str = Field(..., min_length=3)
    marks: conint(ge=0, le=300)

class AlignedQuestion(BaseModel):
    question_no: Optional[str] = None
    question_text: str = Field(..., min_length=5)
    max_marks: conint(ge=1, le=500)
    rubric: List[ParsedRubricItem] = Field(default_factory=list)

class AlignedBatch(BaseModel):
    aligned: List[AlignedQuestion] = Field(..., min_length=1)