import json
import random
from typing import List, Dict, Optional

from unsloth import FastLanguageModel, is_bfloat16_supported
from unsloth.chat_templates import get_chat_template, train_on_responses_only

import torch
from datasets import load_dataset, concatenate_datasets, Dataset
from transformers import TrainingArguments, DataCollatorForSeq2Seq
from trl import SFTTrainer

# Configuration
max_seq_length = 4096  # Choose any! We auto support RoPE Scaling internally!
load_in_4bit = True  # Use 4bit quantization to reduce memory usage. Can be False.
# Probability (0.0 to 1.0) of using "auto" for thinking budget when not specified
auto_budget_probability = 0.2 # You can adjust this (e.g., 0.5 means 50% chance)

# Load Model and Tokenizer
model_name = "unsloth/Qwen3-4B-unsloth-bnb-4bit"
# model_name = "unsloth/Qwen2.5-7B-bnb-4bit"
# model_name = "unsloth/gemma-3-4b-pt-unsloth-bnb-4bit"
# model_name = "unsloth/Llama-3.2-3B-Instruct-bnb-4bit"
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=model_name,
    max_seq_length=max_seq_length,
    load_in_4bit=load_in_4bit,
    # token = "hf_...", # use token if needed
    # You can add other arguments like `attn_implementation="flash_attention_2"`
)

# Apply PEFT (LoRA with DoRA) configuration
model = FastLanguageModel.get_peft_model(
    model,
    r=64,  # Choose any number > 0 ! Suggested 8, 16, 32, 64, 128
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                      "gate_proj", "up_proj", "down_proj",],
    lora_alpha=16,
    lora_dropout=0,  # Supports any, but = 0 is optimized
    bias="none",  # Supports any, but = "none" is optimized
    # [NEW] "unsloth" uses 30% less VRAM, fits 2x larger batch sizes!
    use_gradient_checkpointing="unsloth",  # True or "unsloth" for very long context
    random_state=3407,
    use_rslora=True,  # We support rank stabilized LoRA
    loftq_config=None,  # And LoftQ
    use_dora=False
)

# Get and configure the chat template
# Appropriate for Qwen models
tokenizer = get_chat_template(
    tokenizer,
    chat_template="chatml"
)

# --- Data Loading and Preprocessing ---

print("Loading datasets...")
# Load main dataset
dataset_main = load_dataset("marcodsn/academic-chains-dev", split="train")
# Skip examples with "suitability_score" < 0.5
dataset_main = dataset_main.filter(lambda x: "suitability_score" not in x or x["suitability_score"] >= 0.5)
print(f"Loaded {len(dataset_main)} samples from marcodsn/academic-chains-dev")

# Load samples from the secondary dataset
evol_n = 8000
dataset_evol = load_dataset("arcee-ai/EvolKit-75K", split=f"train[:{evol_n}]") # Take first evol_n samples
print(f"Loaded {len(dataset_evol)} samples from arcee-ai/EvolKit-75K")

def format_academic_chains(examples):
    """
    Format examples from the academic-chains-dev dataset.
    Expects conversations in [{"role": role, "content": content}, ...] format.
    """
    output_texts = []
    num_examples = len(examples[next(iter(examples))])

    for i in range(num_examples):
        convos = examples["conversations"][i]
        avg_thinking_tokens_raw = examples.get("avg_thinking_tokens", [None]*num_examples)[i]

        # Determine thinking budget
        if avg_thinking_tokens_raw is not None and isinstance(avg_thinking_tokens_raw, (int, float)) and avg_thinking_tokens_raw >= 0:
            # approximated_budget = int(avg_thinking_tokens_raw)
            if random.random() < auto_budget_probability:
                approximated_budget = "auto"
            else:
                approximated_budget = int(avg_thinking_tokens_raw)
        else:
            print("Invalid thinking tokens value!!!")
            if random.random() < auto_budget_probability:
                approximated_budget = "auto"
            else:
                approximated_budget = 0

        # Construct system prompt
        system_message = "You are a helpful assistant. Think before answering and put your thoughts between the <think> and </think> tags."
        if approximated_budget == "auto":
            system_message += " Use an appropriate amount of thinking based on the query."
        else:
            system_message += f" Your thinking budget for this conversation is {approximated_budget} tokens."

        # Prepend system message
        formatted_convos = [{"role": "system", "content": system_message}] + convos

        try:
            text = tokenizer.apply_chat_template(
                formatted_convos,
                tokenize=False,
                add_generation_prompt=False
            )
            output_texts.append(text)
        except Exception as e:
            print(f"Error applying chat template: {e} for example {i}")
            output_texts.append("")

    return {"text": output_texts}

def format_evolkit(examples):
    """
    Format examples from the EvolKit dataset, which uses ShareGPT format.
    Expects conversations in [{"from": role, "value": content}, ...] format.
    """
    output_texts = []
    num_examples = len(examples[next(iter(examples))])

    for i in range(num_examples):
        try:
            # Get the conversation data for this example
            conversation_data = examples["conversations"][i]
            convos = []

            # Convert from ShareGPT format to the format expected by the chat template
            for turn in conversation_data:
                # ShareGPT format uses "from" for role and "value" for content
                role = turn.get("from", "").lower()
                content = turn.get("value", "")

                # Map ShareGPT roles to ChatML roles
                if role == "human":
                    role = "user"
                elif role == "gpt":
                    role = "assistant"

                if role and content:  # Ensure we have valid role and content
                    convos.append({"role": role, "content": content})

            # Assign thinking budget
            if random.random() < auto_budget_probability:
                approximated_budget = "auto"
            else:
                approximated_budget = 0

            # Construct system prompt
            system_message = "You are a helpful assistant. Think before answering and put your thoughts between the <think> and </think> tags."
            if approximated_budget == "auto":
                system_message += " Use an appropriate amount of thinking based on the query."
            else:
                system_message += f" Your thinking budget for this conversation is {approximated_budget} tokens."

            # Prepend system message
            # formatted_convos = [{"role": "system", "content": system_message}] + convos
            formatted_convos = convos

            text = tokenizer.apply_chat_template(
                formatted_convos,
                tokenize=False,
                add_generation_prompt=False
            )
            output_texts.append(text)
        except Exception as e:
            print(f"Error formatting EvolKit example {i}: {e}")
            output_texts.append("")

    return {"text": output_texts}


print("Formatting datasets...")
# Apply formatting - important to use batched=True for efficiency
# Note: remove_columns needs to list all original columns to keep only 'text'
print("Formatting main dataset...")
dataset_main_formatted = dataset_main.map(
    format_academic_chains,
    batched=True,
    remove_columns=dataset_main.column_names
)
# print("Formatting evolkit dataset...")
# dataset_evol_formatted = dataset_evol.map(
#     format_evolkit,
#     batched=True,
#     remove_columns=dataset_evol.column_names
# )

# Combine the formatted datasets
# print("Combining datasets...")
# dataset = concatenate_datasets([dataset_main_formatted, dataset_evol_formatted])
# print(f"Combined dataset size before filtering: {len(dataset)}")

dataset = dataset_main_formatted

# Filter out examples that ended up empty after formatting (e.g., due to errors or empty inputs)
dataset = dataset.filter(lambda example: example["text"] is not None and len(example["text"]) > 0)
print(f"Combined dataset size after filtering empty texts: {len(dataset)}")

# Shuffle the final dataset
print("Shuffling dataset...")
dataset = dataset.shuffle(seed=42) # Use a seed for reproducibility


# --- Training Setup ---

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=max_seq_length,
    data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer, padding=True), # Added padding=True, common for DataCollatorForSeq2Seq
    dataset_num_proc=2, # Number of processes for data formatting
    packing=False,  # Can make training 5x faster for short sequences. False is safer for varying lengths.
    args=TrainingArguments(
        per_device_train_batch_size=2, # Adjust based on your VRAM
        gradient_accumulation_steps=8, # Effective batch size = 1 * 8 = 8
        warmup_steps=10, # Adjusted warmup steps slightly
        num_train_epochs=1,  # Set this for full training runs
        # max_steps = 60, # Alternatively, use max_steps for debugging/short runs
        learning_rate=2e-4,
        fp16=not is_bfloat16_supported(),
        bf16=is_bfloat16_supported(),
        logging_steps=1,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="linear",
        seed=3407,
        output_dir="outputs",
        report_to="none",  # Change to "wandb", "tensorboard" etc. if needed
    ),
)

# Configure training on responses only (ChatML format)
trainer = train_on_responses_only(
    trainer,
    # Ensure these match the ChatML format precisely, including newlines
    instruction_part="<|im_start|>user\n",
    response_part="<|im_start|>assistant\n",
)

# --- Start Training ---
print("Starting training...")
trainer_stats = trainer.train()

print("Training finished.")
print("Trainer Stats:", trainer_stats)

# --- Save Model ---
print("Saving final model...")

# Save Merged Model (16-bit)
model.save_pretrained_merged("qwen3-ac", tokenizer)
print("Saved merged 16-bit model to 'qwen3-ac'")

# Save GGUF Model (various quantizations)
# model.save_pretrained_gguf("model_gguf", tokenizer)
# print("Saved base GGUF model to 'model_gguf'")

# model.save_pretrained_gguf("model_q4km_gguf", tokenizer, quantization_method="q4_k_m")
# print("Saved Q4_K_M GGUF model to 'model_q4km_gguf'")

# You can add other GGUF quantizations if needed:
# model.save_pretrained_gguf("model", tokenizer, quantization_method = "q5_k_m")

model.save_pretrained_gguf("qwen3-ac-q8_0", tokenizer)
print("Saved Q8_0 GGUF model to 'qwen3-ac-q8_0'")

print("Model saving complete.")
