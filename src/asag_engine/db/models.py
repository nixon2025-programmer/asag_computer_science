from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base

class Paper(Base):
    __tablename__ = "papers"

    id = Column(String, primary_key=True)

    # Paper identity/metadata
    subject = Column(String, nullable=False)
    grade_level = Column(String, nullable=False)
    topic = Column(String, nullable=True)
    name = Column(String, nullable=True)

    # Versioning / dedupe
    revision = Column(Integer, nullable=False, default=1)   # increments for same (subject, grade, name)
    paper_sha256 = Column(String, nullable=False)
    markscheme_sha256 = Column(String, nullable=False)
    prior_paper_id = Column(String, nullable=True)          # link to previous revision if any

    # Files
    paper_file_path = Column(Text, nullable=False)
    markscheme_file_path = Column(Text, nullable=False)

    # Parse status & audit
    status = Column(String, nullable=False, default="uploaded")  # uploaded | parsed | failed
    parse_raw = Column(Text, nullable=True)
    parse_json = Column(Text, nullable=True)
    parse_error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    questions = relationship("Question", back_populates="paper", cascade="all, delete-orphan")

class Question(Base):
    __tablename__ = "questions"

    id = Column(String, primary_key=True)
    paper_id = Column(String, ForeignKey("papers.id"), nullable=True)

    subject = Column(String, nullable=False)
    grade_level = Column(String, nullable=False)
    topic = Column(String, nullable=True)

    question_no = Column(String, nullable=True)  # e.g., "1(a)"
    question_text = Column(Text, nullable=False)
    max_marks = Column(Integer, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    paper = relationship("Paper", back_populates="questions")
    rubric_items = relationship("RubricItem", back_populates="question", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="question", cascade="all, delete-orphan")

class RubricItem(Base):
    __tablename__ = "rubric_items"

    id = Column(String, primary_key=True)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False)

    point_text = Column(Text, nullable=False)
    marks = Column(Integer, nullable=False)

    keywords_json = Column(Text, nullable=True)

    question = relationship("Question", back_populates="rubric_items")

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(String, primary_key=True)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False)

    student_id = Column(String, nullable=True)
    student_answer = Column(Text, nullable=False)

    llm_raw = Column(Text, nullable=True)
    model_grade_json = Column(Text, nullable=True)
    score_awarded = Column(Float, nullable=True)

    teacher_grade_json = Column(Text, nullable=True)
    final_grade_json = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    question = relationship("Question", back_populates="submissions")