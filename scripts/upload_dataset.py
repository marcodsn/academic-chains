import os
import json
from datasets import load_dataset
from datetime import datetime

# Load the raw dataset
dataset = load_dataset("./dataset/", split="zraw")

# Filter out examples with a value of "avg_thinking_tokens" == 0
raw_num_examples = pre_filter = len(dataset)
dataset = dataset.filter(lambda example: example['avg_thinking_tokens'] != 0)
print(f"Removed no-thinking examples: {pre_filter} -> {len(dataset)}")

# Skip every example that appears before the first example with a value of "model" == "gemini-2.5-pro-exp-03-25"
pre_filter = len(dataset)
skip = 0
for i, example in enumerate(dataset):
    if example['model'] == "gemini-2.5-pro-exp-03-25":
        skip = i
        break
dataset = dataset.select(range(skip, len(dataset)))
print(f"Skipped examples before gemini-2.5-pro-exp-03-25: {pre_filter} -> {len(dataset)}")

# # Convert dates to strings before saving
# def convert_dates_to_str(example):
#     if isinstance(example['paper_published_date'], (datetime)):
#         example['paper_published_date'] = example['paper_published_date'].isoformat()
#     if isinstance(example['paper_updated_date'], (datetime)):
#         example['paper_updated_date'] = example['paper_updated_date'].isoformat()
#     return example

# print("Converting dates to strings...")
# dataset = dataset.map(convert_dates_to_str)

# Save the filtered dataset
output_path = "./dataset/data/train.jsonl"
dataset.to_json(output_path)

# Calculate dataset statistics
train_num_examples = len(dataset)
train_size_bytes = os.path.getsize(output_path)
raw_size_bytes = os.path.getsize("./dataset/data/zraw.jsonl")
dataset_size_bytes = train_size_bytes + raw_size_bytes

# Create or update dataset_info.json
dataset_info_path = "./dataset/dataset_info.json"

# Define the dataset info structure
dataset_info = {
    "description": "This dataset comprises conversations about academic papers in biology and economics. Each conversation contains a 'thinking' section where the model shows the step-by-step reasoning process behind answering questions about the papers.",
    "citation": "",
    "homepage": "",
    "license": "apache-2.0",
    "features": {
        "arxiv_id": {"dtype": "string"},
        "paper_doi": {"dtype": "string"},
        "paper_authors": {"dtype": "list", "feature": {"dtype": "string"}},
        "paper_published_date": {"dtype": "string"},
        "paper_updated_date": {"dtype": "string"},
        "conversations": {
            "dtype": "list",
            "feature": {
                "dtype": "dict",
                "feature": {
                    "role": {"dtype": "string"},
                    "content": {"dtype": "string"}
                }
            }
        },
        "entry_type": {"dtype": "string"},
        "categories": {"dtype": "list", "feature": {"dtype": "string"}},
        "avg_thinking_tokens": {"dtype": "float"},
        "model": {"dtype": "string"}
    },
    "splits": {
        "train": {
            "name": "train",
            "num_bytes": train_size_bytes,
            "num_examples": train_num_examples
        },
        "zraw": {
            "name": "zraw",
            "num_bytes": raw_size_bytes,
            "num_examples": raw_num_examples
        },
        "zraw_curator": {
            "name": "zraw_curator",
            "num_bytes": 0,
            "num_examples": 0
        }
    },
    "download_size": dataset_size_bytes,
    "dataset_size": dataset_size_bytes,
    "pretty_name": "Academic Reasoning and Intuition Chains",
    "tags": [
        "reasoning-datasets-competition",
        "reasoning",
        "academic-papers",
        "question-answering",
        "chain-of-thought",
        "biology",
        "economics"
    ],
    "languages": ["en"]
}

# Write to the dataset_info.json file
with open(dataset_info_path, 'w', encoding='utf-8') as f:
    json.dump(dataset_info, f, indent=2)

print(f"dataset_info.json updated with: {train_num_examples} train examples, {raw_num_examples} raw examples, {dataset_size_bytes} bytes total size")

# Uncomment to push to hub when ready
# dataset.push_to_hub("marcodsn/academic-chains")
