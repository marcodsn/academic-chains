import os
import json
import pandas as pd
import logging
import glob
from tqdm.auto import tqdm

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
DATA_DIR = "./data/jsonls"
OUTPUT_DIR = "./data/jsonls"
OUTPUT_FILE = f"{OUTPUT_DIR}/zprocessed.jsonl"
RAW_SPLIT_PATTERN = f"{DATA_DIR}/zraw*.jsonl"

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Function to get model counts
def get_model_counts(dataframe):
    return dataframe['model'].value_counts().to_dict()

# Function to display model changes
def display_model_changes(before_counts, after_counts, step_name):
    logging.info(f"\n--- Model changes after {step_name} ---")
    all_models = set(list(before_counts.keys()) + list(after_counts.keys()))
    for model in sorted(all_models):
        before = before_counts.get(model, 0)
        after = after_counts.get(model, 0)
        diff = after - before
        change_pct = (diff / before * 100) if before > 0 else float('inf')

        if diff != 0:
            logging.info(f"  {model}: {before} → {after} ({diff:+d}, {change_pct:.2f}%)")

    logging.info("-----------------------------------")

def load_jsonl_files(pattern):
    """Load all JSONL files matching a pattern."""
    all_data = []
    jsonl_files = sorted(glob.glob(pattern))
    logging.info(f"Found {len(jsonl_files)} JSONL files matching pattern '{pattern}'.")

    if not jsonl_files:
        logging.error("No JSONL files found. Exiting.")
        exit()

    for file_path in tqdm(jsonl_files, desc="Reading JSONL files"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        all_data.append(record)
                    except json.JSONDecodeError:
                        logging.warning(f"Skipping invalid JSON line in {file_path}")
        except Exception as e:
            logging.error(f"Error reading file {file_path}: {e}")

    logging.info(f"Read a total of {len(all_data)} records.")
    return all_data

# Load raw dataset
logging.info(f"Loading raw dataset from {RAW_SPLIT_PATTERN}...")
raw_data = load_jsonl_files(RAW_SPLIT_PATTERN)
raw_num_examples = len(raw_data)

# Deduplicate examples
def deduplicate(lines):
    seen = set()
    result = []
    for line in lines:
        line_str = json.dumps(line, sort_keys=True)
        if line_str not in seen:
            seen.add(line_str)
            result.append(line)
    return result

deduplicated_data = deduplicate(raw_data)
logging.info(f"Deduplicated examples: {raw_num_examples} -> {len(deduplicated_data)}")

# Convert to pandas DataFrame
df = pd.DataFrame(deduplicated_data)
logging.info(f"Loaded {len(df)} examples from raw dataset.")

# Get initial model counts
initial_model_counts = get_model_counts(df)
logging.info("\n--- Initial model distribution ---")
for model, count in sorted(initial_model_counts.items(), key=lambda x: x[1], reverse=True):
    logging.info(f"  {model}: {count}")
logging.info("-----------------------------------")

# Filter out examples with avg_thinking_tokens == 0
pre_filter = len(df)
pre_model_counts = get_model_counts(df)
df = df[df['avg_thinking_tokens'] != 0]
post_model_counts = get_model_counts(df)
logging.info(f"Removed no-thinking examples: {pre_filter} -> {len(df)}")
display_model_changes(pre_model_counts, post_model_counts, "removing no-thinking examples")

# Filter examples containing certain phrases
pre_filter = len(df)
pre_model_counts = get_model_counts(df)
df = df[~df['conversations'].astype(str).str.contains("the text|the paper|the doc|The text|The paper|The doc")]
post_model_counts = get_model_counts(df)
logging.info(f"Skipped examples with 'the text', 'the paper' or 'the doc': {pre_filter} -> {len(df)}")
display_model_changes(pre_model_counts, post_model_counts, "filtering specific phrases")

# Filter examples where assistant answer does not end with a period
pre_filter = len(df)
pre_model_counts = get_model_counts(df)

# Define a function to check if the last assistant message ends with a period
def last_assistant_msg_ends_with_period(conversation_list):
    # Get all assistant messages
    assistant_msgs = [msg for msg in conversation_list if msg['role'] == 'assistant']
    if not assistant_msgs:  # If no assistant messages found
        return False
    # Check if the last assistant message ends with a period
    last_msg = assistant_msgs[-1].get('content', '').strip()
    return len(last_msg) > 0 and last_msg[-1] == '.'

# Apply the function to filter the dataframe
df = df[df['conversations'].apply(last_assistant_msg_ends_with_period)]
post_model_counts = get_model_counts(df)

logging.info(f"Skipped examples with assistant answer not ending with a period: {pre_filter} -> {len(df)}")
display_model_changes(pre_model_counts, post_model_counts, "filtering non-period-ending responses")

# Final summary of model changes from start to end
logging.info("\n=== SUMMARY: Model counts from start to end ===")
for model in sorted(set(list(initial_model_counts.keys()) + list(post_model_counts.keys()))):
    initial = initial_model_counts.get(model, 0)
    final = post_model_counts.get(model, 0)
    diff = final - initial
    change_pct = (diff / initial * 100) if initial > 0 else float('inf')

    status = "REMOVED" if final == 0 and initial > 0 else ""

    logging.info(f"{model}: {initial} → {final} ({diff:+d}, {change_pct:.2f}%) {status}")
logging.info("===============================================")

# Define the model ordering (personal preferences on output quality, we will use gemini pro and llama 4 maverick for the rest of data I think)
model_order = [
    "gemini-2.5-pro-exp-03-25",
    "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
    "gemini-2.5-flash-preview-04-17",
    "gemini-2.0-flash",
    "deepseek-ai/DeepSeek-V3"
]

# Create a mapping dictionary for sorting
model_priority = {model: idx for idx, model in enumerate(model_order)}

# Custom sorting function for models
def model_sort_key(model_name):
    # Return the priority if model is in our list, otherwise a high number (low priority)
    return model_priority.get(model_name, len(model_order))

# Create a category for sorting based on the custom order
df['model_priority'] = df['model'].apply(model_sort_key)

# Order the dataset by model priority, then by arxiv_id, then by entry_type
logging.info("Sorting dataset by model priority and then by arxiv_id...")
df = df.sort_values(by=['model_priority', 'arxiv_id', 'entry_type'])

# Drop the temporary column we used for sorting
df = df.drop(columns=['model_priority'])

# Save the filtered dataset
logging.info(f"Saving filtered dataset to {OUTPUT_FILE}...")
df.to_json(OUTPUT_FILE, orient='records', lines=True)

# Calculate dataset statistics
train_num_examples = len(df)
train_size_bytes = os.path.getsize(OUTPUT_FILE)
logging.info(f"Saved filtered dataset with {train_num_examples} examples to {OUTPUT_FILE}")
logging.info(f"Original dataset had {raw_num_examples} examples")
