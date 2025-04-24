import glob
import json
import pandas as pd
import arxiv
from datasets import Dataset
from tqdm.auto import tqdm
import logging
import time

# --- Configuration ---
JSONL_DIR = "data/arxiv_md"  # Directory containing arxiv_*.jsonl files
JSONL_PATTERN = f"{JSONL_DIR}/arxiv_*.jsonl"
HF_DATASET_NAME = "marcodsn/arxiv-markdown"
BATCH_SIZE_ARXIV_API = 100 # How many papers to query from arXiv API at once
REQUEST_DELAY_ARXIV_API = 3 # Seconds to wait between batches (be nice to arXiv!)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Function to Get Metadata ---
def get_arxiv_metadata_batch(arxiv_ids):
    """Fetches metadata for a batch of arXiv IDs."""
    metadata_map = {}
    try:
        search = arxiv.Search(id_list=arxiv_ids, max_results=len(arxiv_ids))
        client = arxiv.Client()
        results = list(client.results(search)) # Fetch all results for the batch

        for result in results:
            # Extract the base ID (without version) if present
            base_id = result.entry_id.split('/')[-1].split('v')[0]
            metadata_map[base_id] = {
                "paper_doi": result.doi,
                "paper_authors": [author.name for author in result.authors],
                "paper_published_date": result.published.isoformat() if result.published else None,
                "paper_updated_date": result.updated.isoformat() if result.updated else None,
                "categories": result.categories,
                "title": result.title,
                "summary": result.summary
            }
            # Also handle potential versioned IDs provided in jsonl
            metadata_map[result.get_short_id()] = metadata_map[base_id]


    except Exception as e:
        logging.error(f"Error fetching batch starting with {arxiv_ids[0] if arxiv_ids else 'N/A'}: {e}")
        # Return empty metadata for all IDs in the batch on error
        for an_id in arxiv_ids:
             # Attempt to extract base ID even on error for default dict
            try:
                base_id = an_id.split('v')[0]
            except:
                base_id = an_id # Fallback if split fails
            metadata_map[base_id] = {
                "paper_doi": None, "paper_authors": [], "paper_published_date": None,
                "paper_updated_date": None, "categories": [], "title": None, "summary": None
            }
            metadata_map[an_id] = metadata_map[base_id] # Add original id too


    # Ensure all requested IDs have an entry, even if fetching failed or paper not found
    for an_id in arxiv_ids:
        base_id = an_id.split('v')[0]
        if base_id not in metadata_map:
             metadata_map[base_id] = {
                "paper_doi": None, "paper_authors": [], "paper_published_date": None,
                "paper_updated_date": None, "categories": [], "title": None, "summary": None
             }
        if an_id not in metadata_map: # Add original id too if missing
             metadata_map[an_id] = metadata_map[base_id]


    return metadata_map


# --- Main Processing ---
logging.info("Starting dataset creation process...")

# 1. Find and read all JSONL files
all_data = []
jsonl_files = sorted(glob.glob(JSONL_PATTERN))
logging.info(f"Found {len(jsonl_files)} JSONL files matching pattern '{JSONL_PATTERN}'.")

if not jsonl_files:
    logging.error("No JSONL files found. Exiting.")
    exit()

for file_path in tqdm(jsonl_files, desc="Reading JSONL files"):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line)
                    # Ensure required keys exist
                    if 'arxiv_id' in record and 'markdown' in record:
                         # Clean arxiv_id (remove 'vX' suffix if present for lookup)
                        clean_id = record['arxiv_id'].split('v')[0]
                        record['clean_arxiv_id'] = clean_id # Store for batching
                        all_data.append(record)
                    else:
                        logging.warning(f"Skipping record in {file_path} due to missing keys: {line.strip()}")
                except json.JSONDecodeError:
                    logging.warning(f"Skipping invalid JSON line in {file_path}: {line.strip()}")
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")

logging.info(f"Read a total of {len(all_data)} records.")

if not all_data:
    logging.error("No valid records found in JSONL files. Exiting.")
    exit()

# 2. Enrich with Metadata using Batching
unique_arxiv_ids = sorted(list(set(item['clean_arxiv_id'] for item in all_data)))
logging.info(f"Found {len(unique_arxiv_ids)} unique arXiv IDs to query.")

all_metadata = {}
for i in tqdm(range(0, len(unique_arxiv_ids), BATCH_SIZE_ARXIV_API), desc="Fetching Metadata"):
    batch_ids = unique_arxiv_ids[i:i + BATCH_SIZE_ARXIV_API]
    batch_metadata = get_arxiv_metadata_batch(batch_ids)
    all_metadata.update(batch_metadata)
    logging.info(f"Fetched metadata for batch {i // BATCH_SIZE_ARXIV_API + 1}, waiting {REQUEST_DELAY_ARXIV_API}s...")
    time.sleep(REQUEST_DELAY_ARXIV_API) # Be nice to the API

logging.info("Finished fetching metadata.")

# 3. Combine original data with metadata
enriched_data = []
for record in tqdm(all_data, desc="Enriching data"):
    metadata = all_metadata.get(record['clean_arxiv_id'], { # Use clean ID for lookup
        "paper_doi": None, "paper_authors": [], "paper_published_date": None,
        "paper_updated_date": None, "categories": [], "title": None, "summary": None
    })
    enriched_record = {
        "arxiv_id": record['arxiv_id'], # Keep original ID
        "markdown": record['markdown'],
        **metadata # Add all fetched metadata fields
    }
    enriched_data.append(enriched_record)

logging.info(f"Successfully enriched {len(enriched_data)} records.")

# 4. Convert to Hugging Face Dataset
# Using a Pandas DataFrame as an intermediate step can be memory-efficient for large datasets
# If memory is a major constraint, consider generating Arrow files directly.
logging.info("Converting to Pandas DataFrame...")
df = pd.DataFrame(enriched_data)

logging.info("Converting DataFrame to Hugging Face Dataset...")
hf_dataset = Dataset.from_pandas(df)

print("\nDataset schema:")
print(hf_dataset.info)
# print("\nExample record:")
# print(hf_dataset[0] if len(hf_dataset) > 0 else "Dataset is empty")


# 5. Upload to Hugging Face Hub
logging.info(f"Pushing dataset to Hugging Face Hub: {HF_DATASET_NAME}")
try:
    hf_dataset.push_to_hub(HF_DATASET_NAME)
    logging.info("Dataset successfully pushed to Hub!")
except Exception as e:
    logging.error(f"Failed to push dataset to Hub: {e}")
    logging.info("You might need to log in using `huggingface-cli login` or check repository permissions.")
