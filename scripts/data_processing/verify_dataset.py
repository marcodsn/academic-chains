import os
import json
import threading
import time
import random
from typing import List, Dict, Set
import uuid
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
    # {
    #     "name": "gemini-2.5-flash-preview-04-17",
    #     "backend_params": {
    #         "api_key": api_key,
    #         "max_requests_per_minute": 10,
    #         "max_tokens_per_minute": 250_000
    #     }
    # }
    # {
    #     "name": "ollama/hf.co/google/gemma-3-27b-it-qat-q4_0-gguf",
    #     "backend": "litellm",
    #     "backend_params": {
    #         "base_url": "http://localhost:11434",
    #         "max_concurrent_requests": 16
    #     }
    # }
    # {
    #     "name": "ollama/hf.co/unsloth/Qwen3-32B-GGUF:Q5_K_XL",
    #     "backend": "litellm",
    #     "backend_params": {
    #         "base_url": "http://localhost:11434",
    #         "max_concurrent_requests": 16
    #     }
    # }
    # {
    #     "name": "ollama/hf.co/unsloth/Qwen3-30B-A3B-GGUF:Q5_K_M",
    #     "backend": "litellm",
    #     "backend_params": {
    #         "base_url": "http://localhost:11434",
    #         "max_concurrent_requests": 16
    #     }
    # }
    {
        "name": "ollama/hf.co/unsloth/Mistral-Small-3.1-24B-Instruct-2503-GGUF:Q4_K_XL",
        "backend": "litellm",
        "backend_params": {
            "base_url": "http://localhost:11434",
            "max_concurrent_requests": 16
        }
    }
    # {
    #     "name": "leon-se/gemma-3-27b-it-qat-W4A16-G128",
    #     "backend": "vllm",
    #     "backend_params": {
    #         "tensor_parallel_size": 1, # Adjust based on GPU count
    #         "gpu_memory_utilization": 0.95,
    #         "max_model_length": 16000,
    #         "max_tokens": 2000
    #     }
    # }
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
def generate_content_id(conversations):
    """Generate a deterministic UUID based on the content of conversations"""
    if conversations is None:
        return str(uuid.uuid4())  # Random UUID if no conversations

    # Convert conversations to a string and encode it
    conv_str = json.dumps(conversations, sort_keys=True)
    # Create a UUID5 using the DNS namespace and the conversation string
    content_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, conv_str))
    return content_id

def get_model_checkpoint_path(model_name: str) -> str:
    """Get the checkpoint path specific to a model."""
    return os.path.join(CHECKPOINT_DIR, f".checkpoint_verifier_{model_name}")

def get_model_output_path(model_name: str) -> str:
    """Get the output path specific to a model."""
    base_name, ext = os.path.splitext(OUTPUT_DATASET_PATH)
    return f"{base_name}_{model_name}{ext}"

def load_checkpoint(checkpoint_path: str) -> Set[str]:
    """Load processed composite keys (arxiv_id_content_id) from checkpoint file."""
    processed_keys = set()
    if os.path.exists(checkpoint_path):
        try:
            with open(checkpoint_path, "r") as f:
                for line in f:
                    composite_key = line.strip()
                    if composite_key:
                        processed_keys.add(composite_key)
        except Exception as e:
            print(f"Warning: Could not load checkpoint {checkpoint_path}. Error: {e}")
    return processed_keys

def save_checkpoint(checkpoint_path: str, composite_key: str):
    """Append composite_key to checkpoint file (thread-safe)."""
    try:
        with file_lock:
            with open(checkpoint_path, "a") as f:
                f.write(f"{composite_key}\n")
    except Exception as e:
        print(f"Error: Could not save checkpoint {checkpoint_path} for key {composite_key}. Error: {e}")

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
        self.model_name = model_name.split("/")[-1]
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
        conversations = item_to_verify.get("conversations", [])

        if not arxiv_id:
            print("Warning: Processing item with missing arxiv_id. Skipping save.")
            return []

        # Generate content_id and create composite key
        content_id = generate_content_id(conversations)
        composite_key = f"{arxiv_id}_{content_id}"

        # Create the augmented result
        augmented_result = item_to_verify.copy()

        # Add content_id to the result
        augmented_result["content_id"] = content_id

        # Store the model-specific verification in the traditional format
        augmented_result["suitability"] = response.classification
        augmented_result["verifier_justification"] = response.justification
        augmented_result["verifier_model"] = self.model_name

        # Save results
        try:
            # Save to model-specific output
            save_result(self.output_path, augmented_result)
            save_checkpoint(self.checkpoint_path, composite_key)

            print(f"Saved verification for {composite_key}. Classification: {response.classification}")
        except Exception as e:
            print(f"Error during saving for {composite_key}: {e}")
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
        model_name = verifier_model["name"].split("/")[-1]
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
                model_name=verifier_model["name"],
                backend=verifier_model["backend"],
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
                        conversations = item.get("conversations")

                        # Basic validation
                        if not arxiv_id:
                            continue
                        if "conversations" not in item or not isinstance(item["conversations"], list):
                            continue

                        # Generate content_id and create composite key
                        content_id = generate_content_id(conversations)
                        composite_key = f"{arxiv_id}_{content_id}"

                        # Check if this model already processed this item
                        if composite_key not in processed_ids:
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
