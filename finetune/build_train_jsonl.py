import argparse
import json
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from asag_engine.db.session import get_session
from asag_engine.db.models import Submission, Question, RubricItem
from asag_engine.grading.prompt import build_grading_prompt

def main():
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=5000)
    args = ap.parse_args()

    session: Session = get_session()
    subs = session.query(Submission).order_by(Submission.created_at.desc()).limit(args.limit).all()

    n = 0
    with open(args.out, "w", encoding="utf-8") as f:
        for s in subs:
            if not s.final_grade_json:
                continue

            q = session.query(Question).filter(Question.id == s.question_id).first()
            if not q:
                continue

            rubric = session.query(RubricItem).filter(RubricItem.question_id == q.id).all()
            if not rubric:
                continue

            system_text, user_text = build_grading_prompt(q, rubric, s.student_answer)
            prompt = f"<|system|>\n{system_text}\n<|user|>\n{user_text}\n<|assistant|>\n"
            record = {"prompt": prompt, "target": s.final_grade_json.strip()}
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            n += 1

    print(f"Wrote {n} examples to {args.out}")

if __name__ == "__main__":
    main()