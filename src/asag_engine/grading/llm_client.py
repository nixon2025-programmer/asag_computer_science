import os
from typing import Optional

class LLMClient:
    def generate(self, system_text: str, user_text: str) -> str:
        raise NotImplementedError

class MindNLPLocalClient(LLMClient):
    def __init__(self, model_id: str, max_new_tokens: int = 768, ms_mode: Optional[str] = None):
        import mindspore as ms
        from mindnlp.transformers import AutoTokenizer, AutoModelForCausalLM

        self.ms = ms
        ms_mode = ms_mode or os.getenv("MS_MODE", "GRAPH_MODE")
        if ms_mode.upper() == "PYNATIVE_MODE":
            self.ms.set_context(mode=self.ms.PYNATIVE_MODE)
        else:
            self.ms.set_context(mode=self.ms.GRAPH_MODE)

        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForCausalLM.from_pretrained(model_id)
        self.max_new_tokens = int(max_new_tokens)

    def _prompt(self, system_text: str, user_text: str) -> str:
        return f"<|system|>\n{system_text}\n<|user|>\n{user_text}\n<|assistant|>\n"

    def generate(self, system_text: str, user_text: str) -> str:
        prompt = self._prompt(system_text, user_text)
        inputs = self.tokenizer(prompt, return_tensors="ms")
        output_ids = self.model.generate(
            **inputs,
            max_new_tokens=self.max_new_tokens,
            do_sample=False
        )
        text = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
        if "<|assistant|>" in text:
            text = text.split("<|assistant|>", 1)[-1].strip()
        return text.strip()

class PanguNLPClient(MindNLPLocalClient):
    # If you have a Pangu checkpoint compatible with MindNLP transformers,
    # set MODEL_ID accordingly and set LLM_PROVIDER=pangu.
    pass

def build_llm_client() -> LLMClient:
    provider = os.getenv("LLM_PROVIDER", "mindnlp").strip().lower()
    model_id = os.getenv("MODEL_ID", "Qwen/Qwen2.5-1.5B-Instruct")
    max_new_tokens = int(os.getenv("MAX_NEW_TOKENS", "768"))

    if provider == "pangu":
        return PanguNLPClient(model_id=model_id, max_new_tokens=max_new_tokens)
    return MindNLPLocalClient(model_id=model_id, max_new_tokens=max_new_tokens)