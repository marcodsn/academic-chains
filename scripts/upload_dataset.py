import os
from datasets import load_dataset, DatasetDict

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

# Skip examples that mention "the text", "the paper" or "the doc" (rough filter for now)
pre_filter = len(dataset)
dataset = dataset.filter(lambda example: "the text" not in str(example['conversations']) and "the paper" not in str(example['conversations']) and "the doc" not in str(example['conversations']))
print(f"Skipped examples with 'the text', 'the paper' or 'the doc': {pre_filter} -> {len(dataset)}")

# Save the filtered dataset
output_path = "./dataset/data/train.jsonl"
dataset.to_json(output_path)

# Calculate dataset statistics
train_num_examples = len(dataset)
train_size_bytes = os.path.getsize(output_path)
print(f"Saved filtered dataset to {output_path}")

# Load all splits for pushing to hub
raw_dataset = load_dataset("./dataset/", split="zraw")
try:
    curator_dataset = load_dataset("./dataset/", split="zraw_curator")
    has_curator = True
except Exception as e:
    print(f"Note: zraw_curator split not loaded: {e}")
    curator_dataset = None
    has_curator = False

# Create a DatasetDict with all splits
full_dataset = DatasetDict({
    "train": dataset,  # This is our filtered dataset
    "zraw": raw_dataset
})
if has_curator:
    full_dataset["zraw_curator"] = curator_dataset

print(f"Prepared dataset with {len(dataset)} train examples, {len(raw_dataset)} raw examples",
      f"and {len(curator_dataset) if has_curator else 0} curator examples")

# Uncomment to push to hub when ready - HuggingFace will handle conversion and metadata
full_dataset.push_to_hub("marcodsn/academic-chains")
