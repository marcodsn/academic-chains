import json
from unsloth import FastLanguageModel
from unsloth.chat_templates import get_chat_template
from trl import SFTTrainer
from transformers import TrainingArguments, DataCollatorForSeq2Seq
from datasets import Dataset
from unsloth import is_bfloat16_supported
from unsloth.chat_templates import train_on_responses_only
import torch
from random import shuffle
from typing import List, Dict

max_seq_length = 48000  # Choose any! We auto support RoPE Scaling internally!
load_in_4bit = True  # Use 4bit quantization to reduce memory usage. Can be False.

model, tokenizer = FastLanguageModel.from_pretrained(
    # model_name = "NousResearch/Hermes-3-Llama-3.2-3B",
    model_name = "unsloth/Llama-3.2-3B-Instruct-bnb-4bit",
    # model_name = "unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit",
    # model_name = "unsloth/Qwen2.5-7B-Instruct-bnb-4bit",
    # model_name = "unsloth/Mistral-Small-3.1-24B-Instruct-2503-bnb-4bit",
    max_seq_length = max_seq_length,
    load_in_4bit = load_in_4bit,
)

model = FastLanguageModel.get_peft_model(
    model,
    r = 16, # Choose any number > 0 ! Suggested 8, 16, 32, 64, 128
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                      "gate_proj", "up_proj", "down_proj",],
    lora_alpha = 16,
    lora_dropout = 0, # Supports any, but = 0 is optimized
    bias = "none",    # Supports any, but = "none" is optimized
    # [NEW] "unsloth" uses 30% less VRAM, fits 2x larger batch sizes!
    use_gradient_checkpointing = "unsloth", # True or "unsloth" for very long context
    random_state = 3407,
    use_rslora = False,  # We support rank stabilized LoRA
    loftq_config = None, # And LoftQ
    use_dora = True
)

tokenizer = get_chat_template(
    tokenizer,
    chat_template = "llama-3.1",
    # chat_template = "qwen-2.5",
    # chat_template = "chatml",
)

def formatting_prompts_func(examples):
    convos = examples["conversations"]
    approximated_budget = examples["avg_thinking_tokens"]
    convos = [{"role": "system", "content": f"You are a helpful assistant. Think before answering and put your thoughts between the <think> and </think> tags. Your thinking budget for this conversation is {approximated_budget} tokens."}] + convos

    if not convos:
        return { "text" : "" }

    text = tokenizer.apply_chat_template(
            convos,
            tokenize = False,
            add_generation_prompt = False
        )
    return { "text" : text, }

dataset = []
with open("../dataset/data/zraw.jsonl", "r") as f:
    for line in f:
        if line.strip():  # Skip empty lines
            try:
                dataset.append(json.loads(line.strip()))
            except json.JSONDecodeError as e:
                print(f"Error parsing line: {e}")

print(f"Pre-filtering: {len(dataset)}")
for entry in dataset:
    if not entry["avg_thinking_tokens"]:
        dataset.remove(entry)
print(f"Post-filtering: {len(dataset)}")
shuffle(dataset)

dataset = Dataset.from_list(dataset)

dataset = dataset.map(
    formatting_prompts_func,
    remove_columns=dataset.column_names
)

# Filter out empty texts
dataset = dataset.filter(lambda example: example["text"] != "")

trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = dataset,
    dataset_text_field = "text",
    max_seq_length = max_seq_length,
    data_collator = DataCollatorForSeq2Seq(tokenizer = tokenizer),
    dataset_num_proc = 2,
    packing = False, # Can make training 5x faster for short sequences.
    args = TrainingArguments(
        per_device_train_batch_size = 1,
        gradient_accumulation_steps = 8,
        warmup_steps = 5,
        num_train_epochs = 2, # Set this for 1 full training run.
        # max_steps = 30,
        learning_rate = 2e-4,
        fp16 = not is_bfloat16_supported(),
        bf16 = is_bfloat16_supported(),
        logging_steps = 1,
        optim = "adamw_8bit",
        weight_decay = 0.01,
        lr_scheduler_type = "linear",
        seed = 3407,
        output_dir = "outputs",
        report_to = "none", # Use this for WandB etc
    ),
)

trainer = train_on_responses_only(
    trainer,
    instruction_part="<|start_header_id|>user<|end_header_id|>\n\n",
    response_part="<|start_header_id|>assistant<|end_header_id|>\n\n",
    # instruction_part = "<|im_start|>user\n",
    # response_part = "<|im_start|>assistant\n",
)

trainer_stats = trainer.train()

model.save_pretrained_merged("model", tokenizer, save_method = "merged_16bit",)
model.save_pretrained_gguf("model", tokenizer,)
model.save_pretrained_gguf("model", tokenizer, quantization_method = "q4_k_m")
