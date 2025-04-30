import os
import pandas as pd
import glob
from tqdm.auto import tqdm
import logging
from datasets import Dataset, DatasetDict

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
DATA_DIR = "./data"
PROCESSED_FILE = f"{DATA_DIR}/jsonls/zverified.jsonl"
# RAW_SPLIT_PATTERN = f"{DATA_DIR}/jsonls/zraw*.jsonl"
# CURATOR_SPLIT_PATTERN = f"{DATA_DIR}/jsonls/zraw_curator*.jsonl"
HF_DATASET_NAME = "marcodsn/academic-chains-dev"

def load_jsonl_file(file_path):
    """Load a single JSONL file."""
    try:
        df = pd.read_json(file_path, lines=True)
        logging.info(f"Loaded {len(df)} examples from {file_path}")
        return df
    except Exception as e:
        logging.error(f"Error loading {file_path}: {e}")
        return pd.DataFrame()

def load_jsonl_files(pattern):
    """Load all JSONL files matching a pattern."""
    all_dfs = []
    jsonl_files = sorted(glob.glob(pattern))
    logging.info(f"Found {len(jsonl_files)} JSONL files matching pattern '{pattern}'.")

    if not jsonl_files:
        logging.warning(f"No JSONL files found matching pattern '{pattern}'.")
        return pd.DataFrame()

    for file_path in tqdm(jsonl_files, desc="Reading JSONL files"):
        df = load_jsonl_file(file_path)
        if not df.empty:
            all_dfs.append(df)

    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        logging.info(f"Combined {len(combined_df)} total records from all files.")
        return combined_df
    else:
        return pd.DataFrame()

# Load the processed training dataset
logging.info(f"Loading processed dataset from {PROCESSED_FILE}...")
if not os.path.exists(PROCESSED_FILE):
    logging.error(f"Processed file {PROCESSED_FILE} does not exist. Run processing.py first.")
    exit(1)

train_df = load_jsonl_file(PROCESSED_FILE)
train_dataset = Dataset.from_pandas(train_df)
logging.info(f"Loaded {len(train_dataset)} training examples.")

# Load the raw dataset
# logging.info(f"Loading raw dataset from {RAW_SPLIT_PATTERN}...")
# raw_df = load_jsonl_files(RAW_SPLIT_PATTERN)
# raw_dataset = Dataset.from_pandas(raw_df)
# logging.info(f"Loaded {len(raw_dataset)} raw examples.")

# Try to load the curator dataset
# logging.info(f"Attempting to load curator dataset from {CURATOR_SPLIT_PATTERN}...")
# has_curator = False
# try:
#     curator_df = load_jsonl_files(CURATOR_SPLIT_PATTERN)
#     if not curator_df.empty:
#         curator_dataset = Dataset.from_pandas(curator_df)
#         has_curator = True
#         logging.info(f"Loaded {len(curator_dataset)} curator examples.")
#     else:
#         logging.info("No curator dataset found.")
#         curator_dataset = None
# except Exception as e:
#     logging.info(f"Note: zraw_curator split not loaded: {e}")
#     curator_dataset = None

# Create a DatasetDict with all splits
full_dataset = DatasetDict({
    "train": train_dataset,
    # "zraw": raw_dataset
})

# if has_curator:
#     full_dataset["zraw_curator"] = curator_dataset

# logging.info(f"Prepared dataset with {len(train_dataset)} train examples, "
#              f"{len(raw_dataset)} raw examples, and "
#              f"{len(curator_dataset) if has_curator else 0} curator examples")

logging.info(f"Prepared dataset with {len(train_dataset)} train examples")

# Push to HuggingFace Hub
logging.info(f"Pushing dataset to Hugging Face Hub: {HF_DATASET_NAME}")
try:
    full_dataset.push_to_hub(HF_DATASET_NAME, revision="main")
    logging.info("Dataset successfully pushed to Hub!")
except Exception as e:
    logging.error(f"Failed to push dataset to Hub: {e}")
    logging.info("You might need to log in using `huggingface-cli login` or check repository permissions.")
