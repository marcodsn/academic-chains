import os
import json
import threading
from dotenv import load_dotenv
from typing import List, Dict, Set
from pydantic import BaseModel, Field
from random import shuffle
from together import Together
from datasets import load_dataset # Added
from transformers import AutoTokenizer
# Removed: from docling.document_converter import DocumentConverter

# --- Initialize Together AI client ---
load_dotenv()
api_key = os.getenv("TOGETHER_API_KEY")
if api_key is None:
    raise ValueError("TOGETHER_API_KEY environment variable not set")
together = Together(api_key=api_key)

# --- Configuration ---
# model = "deepseek-ai/DeepSeek-V3"
model = "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8"


# Define Pydantic models for structured output
class ConversationEntry(BaseModel):
    role: str = Field(description="The role of the participant in the conversation (user or assistant)")
    content: str = Field(description="The content of the message")

class Conversation(BaseModel):
    conversations: List[ConversationEntry] = Field(description="List of conversation entries")

# --- Paths ---
DATASET_DIR = "data/jsonls" # Adjusted directory name
DATASET_PATH = os.path.join(DATASET_DIR, "zraw.jsonl")
CHECKPOINT_DIR = "data" # Adjusted directory name
# Create model-specific checkpoint files
MULTI_SHORT_CHECKPOINT = os.path.join(CHECKPOINT_DIR, f".checkpoint_multi_short_{model.replace('/', '_')}")
SINGLE_LONG_CHECKPOINT = os.path.join(CHECKPOINT_DIR, f".checkpoint_single_long_{model.replace('/', '_')}")

# --- Ensure Directories Exist ---
os.makedirs(DATASET_DIR, exist_ok=True)
os.makedirs(CHECKPOINT_DIR, exist_ok=True)

# --- Thread Lock for File Writing ---
# Ensures safety if you ever introduce concurrency, good practice anyway.
file_lock = threading.Lock()

# --- Checkpointing Functions (Adapted from paste-2.txt) ---
def load_checkpoint(checkpoint_path: str) -> Set[str]:
    """Load processed arxiv_ids from checkpoint file."""
    processed_ids = set()
    if os.path.exists(checkpoint_path):
        try:
            with open(checkpoint_path, "r") as f:
                for line in f:
                    arxiv_id = line.strip()
                    if arxiv_id:
                        processed_ids.add(arxiv_id)
        except Exception as e:
            print(f"Warning: Could not load checkpoint {checkpoint_path}. Error: {e}")
    return processed_ids

def save_checkpoint(checkpoint_path: str, arxiv_id: str):
    """Append arxiv_id to checkpoint file (thread-safe)."""
    try:
        with file_lock:
            with open(checkpoint_path, "a") as f:
                f.write(f"{arxiv_id}\n")
    except Exception as e:
        print(f"Error: Could not save checkpoint {checkpoint_path} for ID {arxiv_id}. Error: {e}")

def save_result(dataset_path: str, result: Dict):
    """Append a single result to the dataset file (thread-safe)."""
    try:
        with file_lock:
            with open(dataset_path, "a") as f:
                f.write(json.dumps(result) + "\n")
    except Exception as e:
        print(f"Error: Could not save result to {dataset_path}. Error: {e}\nResult: {result}")

# --- Loading papers metadata from HuggingFace dataset (Adapted from paste-2.txt) ---
def load_papers_metadata(limit=None): # Added limit parameter
    # Using streaming=True is memory efficient
    dataset = load_dataset("marcodsn/arxiv-markdown", split='train', streaming=True)
    papers_data = []
    print("Loading papers metadata...")
    count = 0
    for item in dataset:
        # Map dataset fields to expected keys
        papers_data.append({
            "arxiv_id": item["arxiv_id"],
            "paper_md": item["markdown"], # Use markdown directly
            "paper_doi": item.get("paper_doi"), # Use .get for safety
            "paper_authors": item.get("paper_authors"),
            "paper_published_date": item.get("paper_published_date"),
            "paper_updated_date": item.get("paper_updated_date"),
            "categories": item.get("categories")
        })
        count += 1
        if count % 1000 == 0:
            print(f"  Loaded {count} papers...")
        if limit is not None and count >= limit:
            print(f"  Reached paper limit ({limit}). Stopping loading.")
            break
    print(f"Finished loading {len(papers_data)} papers.")
    shuffle(papers_data) # Shuffle the list after loading
    return papers_data

# --- Loading Prompts (from paste.txt) ---
def load_prompts():
    prompts = {}
    prompt_dir = "prompts"
    try:
        with open(os.path.join(prompt_dir, "extraction_examples.jsonl"), "r") as f:
            prompts["multi-short"] = f.read()
        with open(os.path.join(prompt_dir, "long_extraction_examples.jsonl"), "r") as f:
            prompts["single-long"] = f.read()

        paper_1_path = os.path.join(prompt_dir, "example_papers/paper_1.md")
        paper_2_path = os.path.join(prompt_dir, "example_papers/paper_2.md")

        if os.path.exists(paper_1_path):
            with open(paper_1_path, "r") as f:
                paper_1_content = f.read()
                prompts["multi-short"] = prompts["multi-short"].replace("{paper_1}", paper_1_content)
                prompts["single-long"] = prompts["single-long"].replace("{paper_1}", paper_1_content)
        else:
            print(f"Warning: Example paper not found at {paper_1_path}")

        if os.path.exists(paper_2_path):
            with open(paper_2_path, "r") as f:
                paper_2_content = f.read()
                prompts["multi-short"] = prompts["multi-short"].replace("{paper_2}", paper_2_content)
                prompts["single-long"] = prompts["single-long"].replace("{paper_2}", paper_2_content)
        else:
            print(f"Warning: Example paper not found at {paper_2_path}")

    except FileNotFoundError as e:
        print(f"Error loading prompts: {e}. Make sure the 'prompts' directory and files exist.")
        raise # Re-raise the exception as prompts are essential
    return prompts

prompts = load_prompts()

# --- Tokenizer and Helper Function ---
# Removed: converter = DocumentConverter()
tokenizer = AutoTokenizer.from_pretrained("unsloth/gemma-3-27b-it") # Or choose another appropriate tokenizer

def _calculate_avg_thinking_tokens(conversations: List[Dict]) -> float:
    """Helper to calculate average thinking tokens from conversation list."""
    total_thinking_tokens = 0
    assistant_replies = 0

    for entry in conversations:
        if entry["role"] == "assistant":
            assistant_replies += 1
            try:
                # Ensure robust splitting even if tags are missing/malformed
                parts = entry["content"].split("<think>", 1)
                if len(parts) > 1:
                    think_content = parts[1].split("</think>", 1)[0].strip()
                    total_thinking_tokens += len(tokenizer.tokenize(think_content))
                # else: No think tag found in this response, token count is 0
            except Exception as e: # Catch potential errors during splitting/tokenizing
                print(f"Warning: Error processing <think> tags: {e} in content: {entry.get('content', '')[:100]}...")

    return total_thinking_tokens / assistant_replies if assistant_replies > 0 else 0.0

# --- Main Dataset Generation Function ---
def generate_dataset(paper_limit=50): # Add limit for testing/cost control
    # Ensure dataset file exists (or create it)
    if not os.path.exists(DATASET_PATH):
        with open(DATASET_PATH, "w") as f:
            pass # Create empty file

    # Load checkpoints
    processed_multi_short = load_checkpoint(MULTI_SHORT_CHECKPOINT)
    processed_single_long = load_checkpoint(SINGLE_LONG_CHECKPOINT)
    print(f"Loaded {len(processed_multi_short)} processed IDs for multi-short from {MULTI_SHORT_CHECKPOINT}")
    print(f"Loaded {len(processed_single_long)} processed IDs for single-long from {SINGLE_LONG_CHECKPOINT}")

    # Load papers metadata from HuggingFace dataset
    papers_metadata = load_papers_metadata(limit=paper_limit)
    total_papers_to_consider = len(papers_metadata)
    print(f"Total papers loaded/to consider: {total_papers_to_consider}")

    processed_count = 0
    skipped_count = 0
    error_count = 0

    for i, paper in enumerate(papers_metadata):
        arxiv_id = paper.get("arxiv_id")
        if not arxiv_id:
            print(f"Warning: Skipping paper at index {i} due to missing arxiv_id.")
            skipped_count += 1
            continue

        print(f"\nProcessing paper {i+1}/{total_papers_to_consider}: {arxiv_id}...")

        try:
            # --- Get Paper Markdown ---
            paper_md = paper.get("paper_md", "")
            if not paper_md:
                print(f"Warning: Skipping paper {arxiv_id} due to empty markdown content.")
                skipped_count += 1
                continue

            # --- Check if Multi-Short processing is needed ---
            generate_multi_short = arxiv_id not in processed_multi_short
            if generate_multi_short:
                print(f"  Generating multi-short entry for {arxiv_id}...")
                prompt_multi_short = prompts["multi-short"].replace("{paper_3}", paper_md)

                try:
                    response = together.chat.completions.create(
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a helpful assistant. Only answer in JSON format.",
                            },
                            {
                                "role": "user",
                                "content": prompt_multi_short
                            }
                        ],
                        model=model,
                        response_format={
                            "type": "json_object",
                            "schema": Conversation.model_json_schema()
                        },
                        # Add other parameters like temperature, max_tokens if needed
                        # max_tokens=500000,
                        # temperature=0.7,
                    )

                    response_content = response.choices[0].message.content
                    response_data = json.loads(response_content) # Parse JSON string
                    conversation_list = response_data.get("conversations", [])

                    avg_tokens = _calculate_avg_thinking_tokens(conversation_list)

                    multi_short_entry = {
                        "arxiv_id": arxiv_id,
                        "paper_doi": paper.get("paper_doi", ""),
                        "paper_authors": paper.get("paper_authors", []),
                        "paper_published_date": paper.get("paper_published_date", ""),
                        "paper_updated_date": paper.get("paper_updated_date", ""),
                        "conversations": conversation_list,
                        "entry_type": "multi-short",
                        "categories": paper.get("categories", []),
                        "avg_thinking_tokens": avg_tokens,
                        "model": model
                    }

                    save_result(DATASET_PATH, multi_short_entry)
                    save_checkpoint(MULTI_SHORT_CHECKPOINT, arxiv_id)
                    print(f"  Successfully generated and saved multi-short for {arxiv_id}")

                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON response for multi-short {arxiv_id}: {e}")
                    print(f"  Raw response content: {response_content[:500]}...") # Log partial raw response
                    # Optionally save failed attempts or retry logic here
                except Exception as e:
                    print(f"Error calling Together API for multi-short {arxiv_id}: {e}")
                    # Optionally save failed attempts or retry logic here
            else:
                print(f"  Skipping multi-short for {arxiv_id} (already processed).")


            # --- Check if Single-Long processing is needed ---
            generate_single_long = arxiv_id not in processed_single_long
            if generate_single_long:
                print(f"  Generating single-long entry for {arxiv_id}...")
                prompt_single_long = prompts["single-long"].replace("{paper_3}", paper_md)

                try:
                    response = together.chat.completions.create(
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a helpful assistant. Only answer in JSON format."
                            },
                            {
                                "role": "user",
                                "content": prompt_single_long
                            }
                        ],
                        model=model,
                        response_format={
                            "type": "json_object",
                            "schema": Conversation.model_json_schema()
                        }
                        # Add other parameters like temperature, max_tokens if needed
                        # max_tokens=500000,
                        # temperature=0.7,
                    )

                    response_content = response.choices[0].message.content
                    response_data = json.loads(response_content) # Parse JSON string
                    conversation_list = response_data.get("conversations", [])

                    avg_tokens = _calculate_avg_thinking_tokens(conversation_list)

                    single_long_entry = {
                        "arxiv_id": arxiv_id,
                        "paper_doi": paper.get("paper_doi", ""),
                        "paper_authors": paper.get("paper_authors", []),
                        "paper_published_date": paper.get("paper_published_date", ""),
                        "paper_updated_date": paper.get("paper_updated_date", ""),
                        "conversations": conversation_list,
                        "entry_type": "single-long",
                        "categories": paper.get("categories", []),
                        "avg_thinking_tokens": avg_tokens,
                        "model": model
                    }

                    save_result(DATASET_PATH, single_long_entry)
                    save_checkpoint(SINGLE_LONG_CHECKPOINT, arxiv_id)
                    print(f"  Successfully generated and saved single-long for {arxiv_id}")

                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON response for single-long {arxiv_id}: {e}")
                    print(f"  Raw response content: {response_content[:500]}...") # Log partial raw response
                    # Optionally save failed attempts or retry logic here
                except Exception as e:
                    print(f"Error calling Together API for single-long {arxiv_id}: {e}")
                    # Optionally save failed attempts or retry logic here
            else:
                print(f"  Skipping single-long for {arxiv_id} (already processed).")

            if not generate_multi_short and not generate_single_long:
                 skipped_count += 1 # Count as skipped if both already done
            else:
                 processed_count += 1 # Count as processed if at least one was generated

        except Exception as e:
            print(f"!!! Critical Error processing paper {arxiv_id}: {e}")
            error_count += 1
            # Decide whether to continue or stop on critical errors

    print("\n--- Dataset Generation Summary ---")
    print(f"Total papers considered: {total_papers_to_consider}")
    print(f"Papers processed (at least one entry generated): {processed_count}")
    print(f"Papers skipped (missing ID, empty markdown, or already processed): {skipped_count}")
    print(f"Papers encountering critical errors during processing loop: {error_count}")
    final_processed_multi = len(load_checkpoint(MULTI_SHORT_CHECKPOINT))
    final_processed_single = len(load_checkpoint(SINGLE_LONG_CHECKPOINT))
    print(f"Final count in multi-short checkpoint: {final_processed_multi}")
    print(f"Final count in single-long checkpoint: {final_processed_single}")
    print(f"Results saved to: {DATASET_PATH}")
    print(f"Checkpoints at: {MULTI_SHORT_CHECKPOINT}, {SINGLE_LONG_CHECKPOINT}")
    print("--- Finished ---")


# --- Call the function to generate the dataset ---
if __name__ == "__main__":
    # You can adjust the paper_limit here for testing, or set to None to process all
    # Be mindful of API costs and rate limits when processing large numbers.
    generate_dataset(paper_limit=250) # Example: Process only the first 50 papers loaded
    # generate_dataset(paper_limit=None) # Uncomment to process all papers from the stream
