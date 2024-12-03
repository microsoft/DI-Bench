from typing import List

from transformers import AutoTokenizer
from vllm import LLM, SamplingParams

from bigbuild.utils.llm.provider.base import BaseProvider
from bigbuild.utils.llm.provider.request import (
    construct_message_list,
    hacky_assistant_stop_seq,
)


class VllmProvider(BaseProvider):
    def __init__(
        self, model, tensor_parallel_size, max_model_len=None, trust_remote_code=False
    ):
        self.tokenizer = AutoTokenizer.from_pretrained(
            model, trust_remote_code=trust_remote_code
        )
        hf_overrides = {}
        if "Qwen/Qwen2.5-Coder" in model:
            hf_overrides["rope_scaling"] = {
                "factor": 4.0,
                "original_max_position_embeddings": 32768,
                "type": "yarn",
            }

        self.llm = LLM(
            model=model,
            tensor_parallel_size=tensor_parallel_size,
            max_model_len=max_model_len,
            trust_remote_code=trust_remote_code,
            hf_overrides=hf_overrides,
        )
        self.stop_seq = []
        if self.tokenizer.chat_template:
            self.stop_seq.append(hacky_assistant_stop_seq(self.tokenizer))

    def generate_reply(
        self, message, n=1, max_tokens=1024, temperature=0.0, system_msg=None
    ) -> List[str]:
        assert temperature != 0 or n == 1, "n must be 1 when temperature is 0"

        prompt = self.tokenizer.apply_chat_template(
            construct_message_list(message, system_msg),
            tokenize=False,
            add_generation_prompt=True,
        )
        vllm_outputs = self.llm.generate(
            [prompt],
            SamplingParams(
                temperature=temperature,
                max_tokens=max_tokens,
                stop=self.stop_seq,
            ),
            use_tqdm=False,
        )

        gen_strs = [x.outputs[0].text for x in vllm_outputs]
        return gen_strs

    def count_tokens(self, message: str, system_message: str) -> int:
        ...
