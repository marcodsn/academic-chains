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
OUTPUT_FILE = f"{OUTPUT_DIR}/train.jsonl"
RAW_SPLIT_PATTERN = f"{DATA_DIR}/zraw*.jsonl"

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

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

# Filter out examples with avg_thinking_tokens == 0
pre_filter = len(df)
df = df[df['avg_thinking_tokens'] != 0]
logging.info(f"Removed no-thinking examples: {pre_filter} -> {len(df)}")

# Filter examples containing certain phrases
pre_filter = len(df)
df = df[~df['conversations'].astype(str).str.contains("the text|the paper|the doc")]
logging.info(f"Skipped examples with 'the text', 'the paper' or 'the doc': {pre_filter} -> {len(df)}")

# Filter examples where assistant answer does not end with a period
pre_filter = len(df)

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

logging.info(f"Skipped examples with assistant answer not ending with a period: {pre_filter} -> {len(df)}")

# Save the filtered dataset
logging.info(f"Saving filtered dataset to {OUTPUT_FILE}...")
df.to_json(OUTPUT_FILE, orient='records', lines=True)

# Calculate dataset statistics
train_num_examples = len(df)
train_size_bytes = os.path.getsize(OUTPUT_FILE)
logging.info(f"Saved filtered dataset with {train_num_examples} examples to {OUTPUT_FILE}")
logging.info(f"Original dataset had {raw_num_examples} examples")
