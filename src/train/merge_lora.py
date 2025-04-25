# from unsloth import FastLanguageModel

# model, tokenizer = FastLanguageModel.from_pretrained(
#     # model_name = "NousResearch/Hermes-3-Llama-3.2-3B",
#     # model_name = "unsloth/Llama-3.2-3B-Instruct-bnb-4bit",
#     # model_name = "unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit",
#     # model_name = "unsloth/Qwen2.5-7B-Instruct-bnb-4bit",
#     model_name = "unsloth/Mistral-Small-3.1-24B-Instruct-2503-bnb-4bit",
#     max_seq_length = 4096,
#     load_in_4bit = True,
# )

# model.load_adapter("outputs/checkpoint-122")

# # Save the merged model
# output_dir = "model_bigger" # Use a different name to avoid conflicts

# model.save_pretrained_merged("model_bigger", tokenizer, save_method = "merged_16bit",)

from peft import AutoPeftModelForConditionalGeneration
import torch

peft_model = AutoPeftModelForConditionalGeneration.from_pretrained(
    "outputs/checkpoint-122",
    low_cpu_mem_usage=True,
    torch_dtype=torch.bfloat16
)
merged_model = peft_model.merge_and_unload()
