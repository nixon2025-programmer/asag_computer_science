from __future__ import annotations
import json
from typing import List, Dict, Tuple
import os

from .chunking import chunk_text
from .extractor import extract_text_from_file
from .schema import ParsedQuestionsLite, AlignedBatch, AlignedQuestion
from .prompt_questions import build_questions_prompt
from .prompt_align import build_align_prompt

def _extract_json_obj(raw: str) -> dict:
    s = raw.find("{")
    e = raw.rfind("}")
    if s == -1 or e == -1 or e <= s:
        raise ValueError("No JSON object found in model output")
    return json.loads(raw[s:e+1])

def extract_questions_from_paper_chunks(
    llm,
    subject: str,
    grade_level: str,
    topic: str | None,
    paper_text: str
) -> Tuple[List[Dict], List[str]]:
    chunk_size = int(os.getenv("PAPER_CHUNK_SIZE", "12000"))
    overlap = int(os.getenv("PAPER_CHUNK_OVERLAP", "800"))

    chunks = chunk_text(paper_text, chunk_size, overlap)
    all_questions: List[Dict] = []
    raw_outputs: List[str] = []

    for ch in chunks:
        sys, usr = build_questions_prompt(subject, grade_level, topic, ch)
        raw = llm.generate(sys, usr)
        raw_outputs.append(raw)
        obj = ParsedQuestionsLite(**_extract_json_obj(raw))

        for q in obj.questions:
            all_questions.append({"question_no": q.question_no, "question_text": q.question_text})

    # Merge/dedupe: normalize by (question_no, first 60 chars)
    seen = set()
    merged = []
    for q in all_questions:
        key = (q.get("question_no") or "").strip().lower(), (q.get("question_text") or "")[:60].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(q)

    if not merged:
        raise ValueError("No questions extracted from paper text. Ensure the PDF/DOCX contains selectable text.")
    return merged, raw_outputs

def align_questions_with_markscheme(
    llm,
    subject: str,
    grade_level: str,
    topic: str | None,
    questions: List[Dict],
    markscheme_text: str
) -> Tuple[List[AlignedQuestion], List[str]]:
    ms_chunk_size = int(os.getenv("MS_CHUNK_SIZE", "14000"))
    ms_overlap = int(os.getenv("MS_CHUNK_OVERLAP", "800"))
    align_batch_size = int(os.getenv("ALIGN_BATCH_SIZE", "5"))

    ms_chunks = chunk_text(markscheme_text, ms_chunk_size, ms_overlap)
    raw_outputs: List[str] = []

    # For each batch of questions, try alignment against all markscheme chunks,
    # keep the best result (most rubric points / marks).
    aligned_final: List[AlignedQuestion] = []

    def score_aligned(a: AlignedQuestion) -> float:
        rubric_marks = sum([float(r.marks) for r in a.rubric]) if a.rubric else 0.0
        return rubric_marks + (0.1 * len(a.rubric))

    for i in range(0, len(questions), align_batch_size):
        batch = questions[i:i+align_batch_size]
        best_by_key: dict[tuple[str, str], AlignedQuestion] = {}

        for ms_ch in ms_chunks:
            sys, usr = build_align_prompt(subject, grade_level, topic, batch, ms_ch)
            raw = llm.generate(sys, usr)
            raw_outputs.append(raw)

            obj = AlignedBatch(**_extract_json_obj(raw))
            for a in obj.aligned:
                key = ((a.question_no or "").strip().lower(), (a.question_text or "")[:60].strip().lower())
                cur = best_by_key.get(key)
                if cur is None or score_aligned(a) > score_aligned(cur):
                    best_by_key[key] = a

        # If some questions not returned, add conservative placeholders
        for q in batch:
            key = ((q.get("question_no") or "").strip().lower(), (q.get("question_text") or "")[:60].strip().lower())
            if key not in best_by_key:
                best_by_key[key] = AlignedQuestion(
                    question_no=q.get("question_no"),
                    question_text=q.get("question_text"),
                    max_marks=2,
                    rubric=[]
                )

        aligned_final.extend(list(best_by_key.values()))

    # Final cleanup: enforce rubric marks <= max_marks, and if rubric sum > max_marks, clamp down proportionally
    cleaned: List[AlignedQuestion] = []
    for a in aligned_final:
        maxm = int(a.max_marks)
        rub = list(a.rubric)

        total = sum(int(r.marks) for r in rub) if rub else 0
        if maxm < 1:
            maxm = 1

        if total > maxm and total > 0 and rub:
            # proportional downscale, but keep ints >=0
            scale = maxm / total
            new_rub = []
            running = 0
            for r in rub:
                nm = int(round(int(r.marks) * scale))
                nm = max(0, nm)
                new_rub.append(type(r)(point_text=r.point_text, marks=nm))
                running += nm
            # fix rounding drift
            if running > maxm:
                # subtract extras from last items
                diff = running - maxm
                for k in range(len(new_rub)-1, -1, -1):
                    if diff <= 0:
                        break
                    take = min(diff, new_rub[k].marks)
                    new_rub[k].marks -= take
                    diff -= take
            rub = new_rub

        cleaned.append(AlignedQuestion(
            question_no=a.question_no,
            question_text=a.question_text,
            max_marks=maxm,
            rubric=rub
        ))

    return cleaned, raw_outputs

def parse_paper_pipeline(
    llm,
    subject: str,
    grade_level: str,
    topic: str | None,
    paper_path: str,
    markscheme_path: str
) -> tuple[list[AlignedQuestion], dict]:
    paper_text = extract_text_from_file(paper_path)
    ms_text = extract_text_from_file(markscheme_path)

    questions, raw_q = extract_questions_from_paper_chunks(llm, subject, grade_level, topic, paper_text)
    aligned, raw_a = align_questions_with_markscheme(llm, subject, grade_level, topic, questions, ms_text)

    audit = {
        "question_extraction_calls": len(raw_q),
        "alignment_calls": len(raw_a),
        "raw_question_outputs": raw_q,
        "raw_alignment_outputs": raw_a,
    }
    return aligned, audit