"""
LoRA Fine-tuning template using MindNLP + MindSpore.

Because MindNLP LoRA/PEFT APIs can vary by version, this script is written as a
clean "template". You may need to adjust the LoRA import path depending on your
installed MindNLP version.

What stays constant:
- Load tokenizer/model via mindnlp.transformers
- Build dataset from JSONL {prompt,target}
- Tokenize prompt+target
- Mask prompt tokens in labels so loss applies to assistant output
- Train adapter weights (LoRA)
"""

import argparse
import json

def load_jsonl(path: str):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True, help="Training JSONL")
    ap.add_argument("--model_id", default="Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--output_dir", default="lora_out")
    ap.add_argument("--max_len", type=int, default=1024)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--lr", type=float, default=1e-4)
    args = ap.parse_args()

    import mindspore as ms
    from mindnlp.transformers import AutoTokenizer, AutoModelForCausalLM

    ms.set_context(mode=ms.GRAPH_MODE)

    tokenizer = AutoTokenizer.from_pretrained(args.model_id)
    model = AutoModelForCausalLM.from_pretrained(args.model_id)

    # ---- LoRA / Adapter injection (TEMPLATE) ----
    # Depending on your MindNLP version, adjust these imports.
    # Common patterns (examples):
    #   from mindnlp.peft import LoraConfig, get_peft_model
    # or:
    #   from mindnlp.transformers.peft import LoraConfig, get_peft_model
    #
    # If your MindNLP build does not include PEFT utilities, upgrade MindNLP
    # and use the built-in adapter tools (still within MindNLP).
    try:
        from mindnlp.peft import LoraConfig, get_peft_model  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "LoRA utilities not found in mindnlp.peft. "
            "Install/upgrade MindNLP to a version that includes PEFT/LoRA."
        ) from e

    lora_config = LoraConfig(
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        target_modules=None  # let library decide or specify module names if required
    )
    model = get_peft_model(model, lora_config)

    # ---- Build tokenized dataset ----
    records = list(load_jsonl(args.train))

    input_ids_list = []
    labels_list = []
    attention_mask_list = []

    for r in records:
        prompt = r["prompt"]
        target = r["target"]

        full_text = prompt + target
        tok = tokenizer(
            full_text,
            max_length=args.max_len,
            truncation=True,
            return_tensors="ms"
        )

        # Labels: copy input_ids then mask prompt tokens as -100
        input_ids = tok["input_ids"][0]
        attn = tok.get("attention_mask", None)
        if attn is None:
            # create a simple attention mask if tokenizer didn't return it
            attn = ms.ops.ones_like(input_ids)

        # Find prompt token length
        tok_prompt = tokenizer(prompt, max_length=args.max_len, truncation=True, return_tensors="ms")
        prompt_len = int(tok_prompt["input_ids"].shape[-1])

        labels = input_ids.copy()
        # mask prompt part
        labels[:prompt_len] = -100

        input_ids_list.append(input_ids)
        labels_list.append(labels)
        attention_mask_list.append(attn)

    # Simple training loop (template)
    # You can replace with MindNLP Trainer if available in your version.
    optimizer = ms.nn.AdamWeightDecay(model.trainable_params(), learning_rate=args.lr)

    loss_fn = ms.nn.CrossEntropyLoss(ignore_index=-100)

    model.set_train(True)

    for epoch in range(args.epochs):
        total_loss = 0.0
        for i in range(len(input_ids_list)):
            input_ids = input_ids_list[i].expand_dims(0)
            labels = labels_list[i].expand_dims(0)
            attention_mask = attention_mask_list[i].expand_dims(0)

            def forward_fn(input_ids, attention_mask, labels):
                outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                logits = outputs.logits  # [B, T, V]
                # shift for causal LM
                shift_logits = logits[:, :-1, :]
                shift_labels = labels[:, 1:]
                loss = loss_fn(
                    shift_logits.reshape(-1, shift_logits.shape[-1]),
                    shift_labels.reshape(-1)
                )
                return loss

            grad_fn = ms.value_and_grad(forward_fn, None, optimizer.parameters, has_aux=False)
            loss, grads = grad_fn(input_ids, attention_mask, labels)
            optimizer(grads)
            total_loss += float(loss.asnumpy())

        avg = total_loss / max(1, len(input_ids_list))
        print(f"Epoch {epoch+1}/{args.epochs} loss={avg:.4f}")

    # Save LoRA adapter
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print(f"Saved LoRA adapter to: {args.output_dir}")

if __name__ == "__main__":
    main()