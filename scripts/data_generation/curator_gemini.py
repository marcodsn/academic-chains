import os
import json
import threading
from typing import List, Dict, Set
from pydantic import BaseModel, Field
from random import shuffle
from datasets import load_dataset
from transformers import AutoTokenizer
from dotenv import load_dotenv

# Import Curator
from bespokelabs import curator

# Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if api_key is None:
    raise ValueError("GEMINI_API_KEY environment variable not set")

# Enable Curator Viewer
# os.environ["CURATOR_VIEWER"]="1"

model = {
    "name": "gemini-2.5-flash-preview-04-17",
    "backend_params": {"api_key": api_key,
    "max_requests_per_minute": 10,
    "max_tokens_per_minute": 250_000
    }
}

# model = {
#     "name": "gemini-2.0-flash",
#     "backend_params": {
#         "api_key": api_key,
#         "max_requests_per_minute": 15,
#         "max_tokens_per_minute": 1_000_000
#     }
# }

# model = {
#     "name": "gemini-2.5-pro-exp-03-25",
#     "backend_params": {"api_key": api_key,
#     "max_requests_per_minute": 5,
#     "max_tokens_per_minute": 250_000
#     }
# }

# Define Pydantic models for structured output
class ConversationEntry(BaseModel):
    role: str = Field(description="The role of the participant in the conversation (user or assistant)")
    content: str = Field(description="The content of the message")

class Conversation(BaseModel):
    conversations: List[ConversationEntry] = Field(description="List of conversation entries")

# --- Paths ---
DATASET_DIR = "data/jsonls"
DATASET_PATH = os.path.join(DATASET_DIR, "zraw.jsonl")
CHECKPOINT_DIR = "data/checkpoints"
MULTI_SHORT_CHECKPOINT = os.path.join(CHECKPOINT_DIR, f".checkpoint_multi_short_{model['name']}")
SINGLE_LONG_CHECKPOINT = os.path.join(CHECKPOINT_DIR, f".checkpoint_single_long_{model['name']}")

# --- Ensure Directories Exist ---
os.makedirs(DATASET_DIR, exist_ok=True)
os.makedirs(CHECKPOINT_DIR, exist_ok=True)

# --- Thread Lock for File Writing ---
# To prevent potential race conditions if Curator ever uses threads internally
# or if we adapt this code for concurrency later.
file_lock = threading.Lock()

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
        # Use lock to ensure thread safety for appending
        with file_lock:
            with open(checkpoint_path, "a") as f:
                f.write(f"{arxiv_id}\n")
    except Exception as e:
        print(f"Error: Could not save checkpoint {checkpoint_path} for ID {arxiv_id}. Error: {e}")

def save_result(dataset_path: str, result: Dict):
    """Append a single result to the dataset file (thread-safe)."""
    try:
        # Use lock to ensure thread safety for appending
        with file_lock:
            with open(dataset_path, "a") as f:
                f.write(json.dumps(result) + "\n")
    except Exception as e:
        print(f"Error: Could not save result to {dataset_path}. Error: {e}\nResult: {result}")


# Loading papers metadata from HuggingFace dataset
def load_papers_metadata():
    # dataset = load_dataset("marcodsn/arxiv-markdown", split='train') # Load only train split
    # Using streaming=True can be memory efficient for large datasets if needed
    dataset = load_dataset("marcodsn/arxiv-markdown", split='train', streaming=True)
    papers_data = []
    print("Loading papers metadata...")
    # If streaming, iterate directly; otherwise, iterate over dataset['train']
    count = 0
    limit = 500  # Optional: Limit the number of papers for testing/cost control
    for item in dataset:
        papers_data.append({
            "arxiv_id": item["arxiv_id"],
            "paper_md": item["markdown"],
            "paper_doi": item["paper_doi"],
            "paper_authors": item["paper_authors"],
            "paper_published_date": item["paper_published_date"],
            "paper_updated_date": item["paper_updated_date"],
            "categories": item["categories"]
        })
        count += 1
        if count % 1000 == 0:
            print(f"  Loaded {count} papers...")
        if count >= limit:
            print(f"  Reached paper limit ({limit}). Stopping loading.")
            break
    print(f"Finished loading {len(papers_data)} papers.")
    shuffle(papers_data)
    return papers_data

# Loading prompts
def load_prompts():
    prompts = {}
    # Make sure paths are correct relative to script execution location
    prompt_dir = "prompts"
    with open(os.path.join(prompt_dir, "extraction_examples.jsonl"), "r") as f:
        prompts["multi-short"] = f.read()
    with open(os.path.join(prompt_dir, "long_extraction_examples.jsonl"), "r") as f:
        prompts["single-long"] = f.read()

    paper_1_path = os.path.join(prompt_dir, "example_papers/paper_1.md")
    paper_2_path = os.path.join(prompt_dir, "example_papers/paper_2.md")
    paper_3_path = os.path.join(prompt_dir, "example_papers/paper_3.md")

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

    if os.path.exists(paper_3_path):
        with open(paper_3_path, "r") as f:
            paper_3_content = f.read()
            prompts["multi-short"] = prompts["multi-short"].replace("{paper_3}", paper_3_content)
            prompts["single-long"] = prompts["single-long"].replace("{paper_3}", paper_3_content)
    else:
        print(f"Warning: Example paper not found at {paper_3_path}")

    return prompts

prompts = load_prompts()

tokenizer = AutoTokenizer.from_pretrained("unsloth/gemma-3-27b-it")

# Define custom LLM classes using Curator
class BaseExtractor(curator.LLM):
    """Base class for common logic and initialization."""
    def __init__(self, dataset_path: str, checkpoint_path: str, entry_type: str, **kwargs):
        super().__init__(**kwargs)
        self.dataset_path = dataset_path
        self.checkpoint_path = checkpoint_path
        self.entry_type = entry_type
        print(f"Initialized {self.__class__.__name__} to save to:")
        print(f"  Dataset: {self.dataset_path}")
        print(f"  Checkpoint: {self.checkpoint_path}")


    def _calculate_avg_thinking_tokens(self, response: Conversation) -> float:
        """Helper to calculate average thinking tokens."""
        total_thinking_tokens = 0
        assistant_replies = 0

        for entry in response.conversations:
            if entry.role == "assistant":
                assistant_replies += 1
                try:
                    # Ensure robust splitting even if tags are missing/malformed
                    parts = entry.content.split("<think>", 1)
                    if len(parts) > 1:
                        think_content = parts[1].split("</think>", 1)[0].strip()
                        total_thinking_tokens += len(tokenizer.tokenize(think_content))
                    # else: No think tag found in this response, token count is 0
                except Exception as e: # Catch potential errors during splitting/tokenizing
                    print(f"Warning: Error processing <think> tags: {e} in content: {entry.content[:100]}...")

        return total_thinking_tokens / assistant_replies if assistant_replies > 0 else 0.0

    def parse(self, paper_data: Dict, response: Conversation) -> List[Dict]:
        """Parses the response, saves result and checkpoint, then returns result."""
        avg_thinking_tokens = self._calculate_avg_thinking_tokens(response)
        arxiv_id = paper_data.get("arxiv_id", "UNKNOWN_ID") # Ensure ID exists

        result = {
            "arxiv_id": arxiv_id,
            "paper_doi": paper_data.get("paper_doi", ""),
            "paper_authors": paper_data.get("paper_authors", []),
            "paper_published_date": paper_data.get("paper_published_date", ""),
            "paper_updated_date": paper_data.get("paper_updated_date", ""),
            "conversations": [{"role": entry.role, "content": entry.content} for entry in response.conversations],
            "entry_type": self.entry_type,
            "categories": paper_data.get("categories", []),
            "avg_thinking_tokens": avg_thinking_tokens,
            "model": model["name"]
        }

        # --- Incremental Saving ---
        if arxiv_id != "UNKNOWN_ID":
            save_result(self.dataset_path, result)
            save_checkpoint(self.checkpoint_path, arxiv_id)
            # Optional: Add a print statement for progress
            # print(f"Saved {self.entry_type} result for {arxiv_id}")
        else:
            print(f"Warning: Skipping save for entry with missing arxiv_id. Data: {paper_data}")


        # Return the result list as expected by Curator
        return [result]

class MultiShortExtractor(BaseExtractor):
    def __init__(self, **kwargs):
        # Pass specific paths and type, along with other args to BaseExtractor
        super().__init__(
            dataset_path=DATASET_PATH,
            checkpoint_path=MULTI_SHORT_CHECKPOINT,
            entry_type="multi-short",
            **kwargs
        )

    def prompt(self, paper_data: Dict) -> str:
        paper_md = paper_data.get("paper_md", "") # Use .get for safety
        if "{paper_4}" not in prompts["multi-short"]:
             print("Warning: Placeholder '{paper_4}' not found in multi-short prompt template.")
             return prompts["multi-short"] # Return template as is or handle error
        if not paper_md:
            print(f"Warning: Empty paper_md for arxiv_id {paper_data.get('arxiv_id')}")
            # Decide how to handle empty markdown - skip or use a placeholder?
            # Returning an empty string or raising an error might be appropriate
            # For now, let's proceed but it might cause issues downstream
            return prompts["multi-short"].replace("{paper_4}", "[PAPER MARKDOWN MISSING]")
        return prompts["multi-short"].replace("{paper_4}", paper_md)

class SingleLongExtractor(BaseExtractor):
    def __init__(self, **kwargs):
        # Pass specific paths and type, along with other args to BaseExtractor
        super().__init__(
            dataset_path=DATASET_PATH,
            checkpoint_path=SINGLE_LONG_CHECKPOINT,
            entry_type="single-long",
            **kwargs
        )

    def prompt(self, paper_data: Dict) -> str:
        paper_md = paper_data.get("paper_md", "") # Use .get for safety
        if "{paper_4}" not in prompts["single-long"]:
             print("Warning: Placeholder '{paper_4}' not found in single-long prompt template.")
             return prompts["single-long"] # Return template as is or handle error
        if not paper_md:
            print(f"Warning: Empty paper_md for arxiv_id {paper_data.get('arxiv_id')}")
            return prompts["single-long"].replace("{paper_4}", "[PAPER MARKDOWN MISSING]")
        return prompts["single-long"].replace("{paper_4}", paper_md)


def generate_dataset():
    """Generate dataset by processing papers, saving incrementally."""

    # Initialize empty dataset file if it doesn't exist
    if not os.path.exists(DATASET_PATH):
        with open(DATASET_PATH, "w") as _:
            pass # Create empty file

    # Load checkpoints
    processed_multi_short = load_checkpoint(MULTI_SHORT_CHECKPOINT)
    processed_single_long = load_checkpoint(SINGLE_LONG_CHECKPOINT)

    print(f"Found {len(processed_multi_short)} papers already processed with multi-short extractor (checkpoint: {MULTI_SHORT_CHECKPOINT})")
    print(f"Found {len(processed_single_long)} papers already processed with single-long extractor (checkpoint: {SINGLE_LONG_CHECKPOINT})")

    # Load all papers metadata
    papers_metadata_all = load_papers_metadata()
    total_papers_loaded = len(papers_metadata_all)
    print(f"Total papers loaded: {total_papers_loaded}")

    # Filter out already processed papers
    papers_for_multi_short = [
        paper for paper in papers_metadata_all
        if paper.get("arxiv_id") and paper.get("arxiv_id") not in processed_multi_short
    ]
    papers_for_single_long = [
        paper for paper in papers_metadata_all
        if paper.get("arxiv_id") and paper.get("arxiv_id") not in processed_single_long
    ]

    print(f"Processing {len(papers_for_multi_short)} new papers with multi-short extractor")
    print(f"Processing {len(papers_for_single_long)} new papers with single-long extractor")

    # Initialize extractors (passing necessary args)
    multi_short_extractor = MultiShortExtractor(
        model_name="gemini/" + model["name"],
        backend="litellm",
        backend_params=model["backend_params"],
        response_format=Conversation,
        batch=False # Keep batch=False if processing with rate limits, otherwise you will get an error
    )

    single_long_extractor = SingleLongExtractor(
        model_name="gemini/" + model["name"],
        backend="litellm",
        backend_params=model["backend_params"],
        response_format=Conversation,
        batch=False
    )

    # Process with multi-short extractor
    # Curator's call will iterate, call prompt, call API, call parse (which saves)
    if papers_for_multi_short:
        print("\n--- Starting Multi-Short Extraction ({len(papers_for_multi_short)} papers) ---")
        # The results are saved *during* this call by the parse method.
        # We don't strictly need the return value unless Curator needs it or for final counts.
        multi_short_results = multi_short_extractor(papers_for_multi_short)
        print("--- Finished Multi-Short Extraction ---")
        # Optional: Check if len(multi_short_results) matches len(papers_for_multi_short)
        # This can help detect if curator skipped items due to internal errors.
        print(f"  Expected: {len(papers_for_multi_short)}, Curator processed: {len(multi_short_results)}")


    # Process with single-long extractor
    if papers_for_single_long:
        print("\n--- Starting Single-Long Extraction ({len(papers_for_single_long)} papers) ---")
        # The results are saved *during* this call by the parse method.
        single_long_results = single_long_extractor(papers_for_single_long)
        print("--- Finished Single-Long Extraction ---")
        print(f"  Expected: {len(papers_for_single_long)}, Curator processed: {len(single_long_results)}")

    # Recalculate final counts based on potentially updated checkpoints
    final_processed_multi_short = load_checkpoint(MULTI_SHORT_CHECKPOINT)
    final_processed_single_long = load_checkpoint(SINGLE_LONG_CHECKPOINT)

    print("\nDataset generation attempt complete.")
    print(f"Results saved incrementally to {DATASET_PATH}")
    print(f"Checkpoints updated incrementally at {MULTI_SHORT_CHECKPOINT} and {SINGLE_LONG_CHECKPOINT}")
    print("Total papers processed according to checkpoints:")
    print(f"  Multi-short: {len(final_processed_multi_short)}")
    print(f"  Single-long: {len(final_processed_single_long)}")


# Call the function to generate the dataset
if __name__ == "__main__":
    generate_dataset()
