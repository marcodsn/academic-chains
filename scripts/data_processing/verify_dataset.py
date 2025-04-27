import os
import json
import threading
import time
import random
from typing import List, Dict, Set
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv
import traceback # For better error logging

# Import Curator
from bespokelabs import curator

# Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if api_key is None:
    raise ValueError("GEMINI_API_KEY environment variable not set")

# --- Model Configuration ---
# List of verifier models
verifier_models = [
    # {
    #     "name": "gemini-2.0-flash",
    #     "backend_params": {
    #         "api_key": api_key,
    #         "max_requests_per_minute": 15,
    #         "max_tokens_per_minute": 1_000_000,
    #     }
    # },
    {
        "name": "gemini-2.5-flash-preview-04-17",
        "backend_params": {
            "api_key": api_key,
            "max_requests_per_minute": 10,
            "max_tokens_per_minute": 250_000
        }
    }
]

# --- Paths ---
INPUT_DATASET_PATH = "data/jsonls/zprocessed.jsonl"
OUTPUT_DATASET_PATH = "data/jsonls/zverified.jsonl"
CHECKPOINT_DIR = "data/checkpoints"
VERIFIER_PROMPT_PATH = "./prompts/verifier.jsonl"

# --- Ensure Directories Exist ---
os.makedirs(os.path.dirname(INPUT_DATASET_PATH), exist_ok=True)
os.makedirs(os.path.dirname(OUTPUT_DATASET_PATH), exist_ok=True)
os.makedirs(CHECKPOINT_DIR, exist_ok=True)

# --- Thread Lock for File Writing ---
file_lock = threading.Lock()

# --- Pydantic Models ---
class ConversationEntry(BaseModel):
    role: str
    content: str

class VerificationResult(BaseModel):
    classification: str = Field(description="The classification ('Suitable' or 'Unsuitable')")
    justification: str = Field(description="The justification for the classification")

    @validator('classification')
    def classification_must_be_valid(cls, v):
        if v not in ["Suitable", "Unsuitable"]:
            # Try to leniently correct common misspellings or case issues
            v_lower = v.lower().strip()
            if v_lower == "suitable":
                return "Suitable"
            if v_lower == "unsuitable":
                return "Unsuitable"
            raise ValueError('Classification must be either "Suitable" or "Unsuitable"')
        return v

# --- Helper Functions ---
def get_model_checkpoint_path(model_name: str) -> str:
    """Get the checkpoint path specific to a model."""
    return os.path.join(CHECKPOINT_DIR, f".checkpoint_verifier_{model_name}")

def get_model_output_path(model_name: str) -> str:
    """Get the output path specific to a model."""
    base_name, ext = os.path.splitext(OUTPUT_DATASET_PATH)
    return f"{base_name}_{model_name}{ext}"

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

def save_result(output_path: str, result: Dict):
    """Append a single verified result to the output dataset file (thread-safe)."""
    try:
        with file_lock:
            with open(output_path, "a") as f:
                f.write(json.dumps(result) + "\n")
    except Exception as e:
        print(f"Error: Could not save result to {output_path}. Error: {e}\nResult: {result}")

def load_verifier_prompt(prompt_path: str) -> str:
    """Loads the verifier prompt template."""
    try:
        with open(prompt_path, "r") as f:
            prompt_template = f.read()
        if not prompt_template:
            raise ValueError(f"Verifier prompt file is empty: {prompt_path}")
        if "{qa_pair_json}" not in prompt_template:
             raise ValueError("Verifier prompt template must contain the placeholder '{qa_pair_json}'")
        return prompt_template
    except FileNotFoundError:
        print(f"Error: Verifier prompt file not found at {prompt_path}")
        raise
    except Exception as e:
        print(f"Error loading verifier prompt: {e}")
        raise

# --- Curator Verifier LLM Class ---
class VerifierLLM(curator.LLM):
    def __init__(self, prompt_template: str, output_path: str, checkpoint_path: str, model_name: str, **kwargs):
        super().__init__(model_name, **kwargs)
        self.prompt_template = prompt_template
        self.output_path = output_path
        self.checkpoint_path = checkpoint_path
        self.model_name = "".join(model_name.split("/")[1:])
        print(f"Initialized VerifierLLM with model: {self.model_name}")
        print(f"  Saving results to: {self.output_path}")
        print(f"  Updating checkpoint: {self.checkpoint_path}")

    def prompt(self, item_to_verify: Dict) -> str:
        """Formats the prompt for the verifier LLM."""
        conversation = item_to_verify.get("conversations", [])
        arxiv_id = item_to_verify.get("arxiv_id", "Unknown ID")

        if not conversation:
            print(f"Warning: No 'conversations' found in item: {arxiv_id}")
            conversation_json_str = json.dumps({"conversations": []})
        else:
            conversation_json_str = json.dumps({"conversations": conversation}, indent=2)

        try:
            formatted_prompt = self.prompt_template.replace("{qa_pair_json}", conversation_json_str)
            return formatted_prompt
        except Exception as e:
            print(f"Error formatting prompt for {arxiv_id}: {e}")
            return ""

    def parse(self, item_to_verify: Dict, response: VerificationResult) -> List[Dict]:
        """
        Parses the structured response and saves the verification result.
        """
        arxiv_id = item_to_verify.get("arxiv_id")

        if not arxiv_id:
            print("Warning: Processing item with missing arxiv_id. Skipping save.")
            return []

        # Create the augmented result
        augmented_result = item_to_verify.copy()

        # Store the model-specific verification in the traditional format
        augmented_result["suitability"] = response.classification
        augmented_result["verifier_justification"] = response.justification
        augmented_result["verifier_model"] = self.model_name

        # Save results
        try:
            # Save to model-specific output
            save_result(self.output_path, augmented_result)
            save_checkpoint(self.checkpoint_path, arxiv_id)

            print(f"Saved verification for {arxiv_id}. Classification: {response.classification}")
        except Exception as e:
            print(f"Error during saving for {arxiv_id}: {e}")
            traceback.print_exc()

        return [augmented_result]

# --- Main Verification Function ---
def verify_dataset():
    """Process dataset with multiple verifier models."""

    print("Starting multi-verifier ensemble verification process...")
    print(f"Input dataset: {INPUT_DATASET_PATH}")
    print(f"Using {len(verifier_models)} verifier models")

    # Load verifier prompt template
    try:
        verifier_prompt_template = load_verifier_prompt(VERIFIER_PROMPT_PATH)
    except Exception:
        print("Failed to load verifier prompt. Exiting.")
        return

    # Process with each verifier model
    for verifier_model in verifier_models:
        model_name = verifier_model["name"]
        model_checkpoint_path = get_model_checkpoint_path(model_name)
        model_output_path = get_model_output_path(model_name)

        print(f"\n=== Processing with verifier model: {model_name} ===")
        print(f"Model checkpoint: {model_checkpoint_path}")
        print(f"Model output: {model_output_path}")

        # Load checkpoint for this model
        processed_ids = load_checkpoint(model_checkpoint_path)
        print(f"Loaded {len(processed_ids)} processed IDs from checkpoint for model {model_name}.")

        # Initialize VerifierLLM for this model
        try:
            verifier_llm = VerifierLLM(
                prompt_template=verifier_prompt_template,
                output_path=model_output_path,
                checkpoint_path=model_checkpoint_path,
                model_name="gemini/" + model_name,
                backend="litellm",
                backend_params=verifier_model["backend_params"],
                response_format=VerificationResult,
                batch=False
            )
        except Exception as e:
            print(f"Failed to initialize VerifierLLM for model {model_name}: {e}")
            traceback.print_exc()
            continue

        # Identify items this model hasn't processed yet
        items_to_process = []
        initial_count = 0

        if not os.path.exists(INPUT_DATASET_PATH):
            print(f"Error: Input file not found: {INPUT_DATASET_PATH}")
            continue

        try:
            with open(INPUT_DATASET_PATH, "r") as infile:
                for i, line in enumerate(infile):
                    initial_count += 1
                    try:
                        item = json.loads(line)
                        arxiv_id = item.get("arxiv_id")

                        # Basic validation
                        if not arxiv_id:
                            continue
                        if "conversations" not in item or not isinstance(item["conversations"], list):
                            continue

                        # Check if this model already processed this item
                        if arxiv_id not in processed_ids:
                            items_to_process.append(item)
                    except Exception:
                        continue
        except Exception as e:
            print(f"Error reading input file {INPUT_DATASET_PATH}: {e}")
            continue

        # Shuffle items to process
        random.shuffle(items_to_process)

        total_to_process = len(items_to_process)
        print(f"Found {total_to_process} new items to verify with model {model_name}.")

        if not items_to_process:
            print(f"No new items to verify with model {model_name}. Continuing to next model.")
            continue

        # Ensure output file exists
        os.makedirs(os.path.dirname(model_output_path), exist_ok=True)
        try:
            with open(model_output_path, "a") as _:
                pass
        except Exception as e:
            print(f"Error creating output file for model {model_name}: {e}")
            continue

        # Process items with this model
        start_time = time.time()
        try:
            verification_results = verifier_llm(items_to_process)
            processed_count = len(verification_results)
            error_count = total_to_process - processed_count

            print(f"\nFinished processing with model {model_name}")
            print(f"Successfully processed: {processed_count} items")
            print(f"Errors: {error_count} items")
        except Exception as e:
            print(f"Error during verification with model {model_name}: {e}")
            traceback.print_exc()
        finally:
            end_time = time.time()
            total_time = end_time - start_time
            print(f"Total time for model {model_name}: {total_time:.2f} seconds")

    print("\nVerification complete. Run the merge_verification_results.py script to merge all verifier outputs.")

# --- Run the Verification ---
if __name__ == "__main__":
    verify_dataset()
