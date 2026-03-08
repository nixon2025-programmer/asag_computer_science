# Fine-tuning (LoRA) – MindNLP

Gold data comes from teacher overrides:
- POST /api/v1/grade creates submissions
- PATCH /api/v1/submissions/<id>/override creates gold labels

Export JSONL:
export PYTHONPATH=./src
python finetune/build_train_jsonl.py --out train.jsonl --limit 5000

Train LoRA:
python finetune/train_lora_qwen25_15b.py --train train.jsonl --model_id Qwen/Qwen2.5-1.5B-Instruct --output_dir lora_out