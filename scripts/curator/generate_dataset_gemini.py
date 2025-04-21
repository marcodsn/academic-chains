import os
import json
import queue
import threading
import concurrent.futures
from dotenv import load_dotenv
from typing import List, Dict
from pydantic import BaseModel, Field
from random import shuffle

# Import Curator
from bespokelabs import curator

from docling.document_converter import DocumentConverter
from transformers import AutoTokenizer

# Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if api_key is None:
    raise ValueError("GEMINI_API_KEY environment variable not set")

# Enable Curator Viewer
# os.environ["CURATOR_VIEWER"]="1"

model = "gemini-2.5-flash-preview-04-17"

# Define Pydantic models for structured output
class ConversationEntry(BaseModel):
    role: str = Field(description="The role of the participant in the conversation (user or assistant)")
    content: str = Field(description="The content of the message")

class Conversation(BaseModel):
    conversations: List[ConversationEntry] = Field(description="List of conversation entries")

# Loading papers metadata
papers_metadata = []
with open("data/arxiv_metadata.jsonl", "r") as f:
    for line in f:
        papers_metadata.append(json.loads(line))
shuffle(papers_metadata)

# Loading prompts
prompts = {}
with open("prompts/extraction_examples.jsonl", "r") as f:
    prompts["multi-short"] = f.read()
with open("prompts/long_extraction_examples.jsonl", "r") as f:
    prompts["single-long"] = f.read()

with open("prompts/example_papers/paper_1.md", "r") as f:
    paper_1_content = f.read()
    prompts["multi-short"] = prompts["multi-short"].replace("{paper_1}", paper_1_content)
    prompts["single-long"] = prompts["single-long"].replace("{paper_1}", paper_1_content)

with open("prompts/example_papers/paper_2.md", "r") as f:
    paper_2_content = f.read()
    prompts["multi-short"] = prompts["multi-short"].replace("{paper_2}", paper_2_content)
    prompts["single-long"] = prompts["single-long"].replace("{paper_2}", paper_2_content)

# Defining functions
converter = DocumentConverter()
tokenizer = AutoTokenizer.from_pretrained("unsloth/gemma-3-27b-it")

# Define custom LLM classes using Curator
class MultiShortExtractor(curator.LLM):
    def prompt(self, paper_data: Dict) -> str:
        paper_md = paper_data["paper_md"]
        return prompts["multi-short"].replace("{paper_3}", paper_md)

    def parse(self, paper_data: Dict, response: Conversation) -> List[Dict]:
        # Calculate average thinking tokens
        avg_thinking_tokens = 0
        assistant_replies = 0

        for entry in response.conversations:
            if entry.role == "assistant":
                assistant_replies += 1
                # Extract thinking section between <think> tags
                try:
                    think_content = entry.content.split("<think>")[1].split("</think>")[0].strip()
                    avg_thinking_tokens += len(tokenizer.tokenize(think_content))
                except IndexError:
                    print("Warning: Could not find <think>...</think> tags in assistant message")

        if assistant_replies > 0:
            avg_thinking_tokens /= assistant_replies
        else:
            avg_thinking_tokens = 0

        result = {
            "arxiv_id": paper_data.get("arxiv_id", ""),
            "paper_doi": paper_data.get("doi", ""),
            "paper_authors": paper_data.get("authors", []),
            "paper_published_date": paper_data.get("published_date", ""),
            "paper_updated_date": paper_data.get("updated_date", ""),
            "conversations": [{"role": entry.role, "content": entry.content} for entry in response.conversations],
            "entry_type": "multi-short",
            "categories": paper_data.get("categories", []),
            "avg_thinking_tokens": avg_thinking_tokens,
            "model": model
        }
        return [result]

class SingleLongExtractor(curator.LLM):
    def prompt(self, paper_data: Dict) -> str:
        paper_md = paper_data["paper_md"]
        return prompts["single-long"].replace("{paper_3}", paper_md)

    def parse(self, paper_data: Dict, response: Conversation) -> List[Dict]:
        # Calculate average thinking tokens
        avg_thinking_tokens = 0
        assistant_replies = 0

        for entry in response.conversations:
            if entry.role == "assistant":
                assistant_replies += 1
                # Extract thinking section between <think> tags
                try:
                    think_content = entry.content.split("<think>")[1].split("</think>")[0].strip()
                    avg_thinking_tokens += len(tokenizer.tokenize(think_content))
                except IndexError:
                    print("Warning: Could not find <think>...</think> tags in assistant message")

        if assistant_replies > 0:
            avg_thinking_tokens /= assistant_replies
        else:
            avg_thinking_tokens = 0

        result = {
            "arxiv_id": paper_data.get("arxiv_id", ""),
            "paper_doi": paper_data.get("doi", ""),
            "paper_authors": paper_data.get("authors", []),
            "paper_published_date": paper_data.get("published_date", ""),
            "paper_updated_date": paper_data.get("updated_date", ""),
            "conversations": [{"role": entry.role, "content": entry.content} for entry in response.conversations],
            "entry_type": "single-long",
            "categories": paper_data.get("categories", []),
            "avg_thinking_tokens": avg_thinking_tokens,
            "model": model
        }
        return [result]

def generate_dataset():
    dataset_path = "dataset/data/zraw_curator.jsonl"

    # Ensure directory exists
    os.makedirs(os.path.dirname(dataset_path), exist_ok=True)

    # Initialize Curator extractors
    multi_short_extractor = MultiShortExtractor(
        model_name="gemini/" + model,
        backend="litellm",
        backend_params={
            "api_key": api_key,
            "max_requests_per_minute": 10,
            "max_tokens_per_minute": 250_000
        },
        response_format=Conversation,
        batch=False
    )

    single_long_extractor = SingleLongExtractor(
        model_name="gemini/" + model,
        backend="litellm",
        backend_params={
            "api_key": api_key,
            "max_requests_per_minute": 10,
            "max_tokens_per_minute": 250_000
        },
        response_format=Conversation,
        batch=False
    )

    # Function to convert PDF to markdown (this is our metadata download function)
    def download_paper_md(paper):
        try:
            print(f"Converting paper {paper.get('arxiv_id', 'unknown')}...")
            paper_doc = converter.convert(paper["pdf_url"])
            paper_md = paper_doc.document.export_to_markdown()

            # Return paper data with markdown
            return {
                **paper,
                "paper_md": paper_md
            }
        except Exception as e:
            print(f"Error converting paper {paper.get('arxiv_id', 'unknown')}: {e}")
            return None

    # Function to process a batch of papers with both extractors
    def process_batch(paper_batch):
        with open(dataset_path, "a") as output_file:
            # Process with multi-short extractor
            try:
                multi_short_results = multi_short_extractor(paper_batch)
                for result in multi_short_results:
                    output_file.write(json.dumps(result) + "\n")
                print(f"Processed batch of {len(paper_batch)} papers with multi-short extractor")
            except Exception as e:
                print(f"Error with multi-short extraction: {e}")

            # Process with single-long extractor
            try:
                single_long_results = single_long_extractor(paper_batch)
                for result in single_long_results:
                    output_file.write(json.dumps(result) + "\n")
                print(f"Processed batch of {len(paper_batch)} papers with single-long extractor")
            except Exception as e:
                print(f"Error with single-long extraction: {e}")

    # Check if the dataset file already exists
    if os.path.exists(dataset_path):
        pass
    else:
        # Create empty file to start with
        with open(dataset_path, "w") as f:
            pass

    # Define batch size and prefetch parameters
    batch_size = int(os.environ.get("CURATOR_BATCH_SIZE", 8))
    prefetch_factor = 3  # Prefetch up to 3x the batch size
    max_download_workers = 1  # Maximum number of parallel downloaders

    # Create a bounded queue for prefetching
    metadata_queue = queue.Queue(maxsize=prefetch_factor * batch_size)

    # Sentinel value to signal the end of data
    END_SENTINEL = object()

    # Function to run in a separate thread - handles downloading
    def downloader_thread():
        try:
            # Use ThreadPoolExecutor for parallel downloads
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_download_workers) as executor:
                # Submit all downloads
                future_to_paper = {executor.submit(download_paper_md, paper): paper for paper in papers_metadata}

                # Process results as they complete
                for future in concurrent.futures.as_completed(future_to_paper):
                    paper = future_to_paper[future]
                    try:
                        paper_data = future.result()

                        # Skip None results (failed downloads)
                        if paper_data is not None:
                            # This will block if queue is full, limiting prefetching
                            metadata_queue.put(paper_data)
                    except Exception as e:
                        print(f"Unexpected error processing result from {paper.get('arxiv_id', 'unknown')}: {e}")
        finally:
            # Ensure sentinel is added even if there's an unexpected error
            metadata_queue.put(END_SENTINEL)

    # Start the downloader thread
    downloader = threading.Thread(target=downloader_thread)
    downloader.daemon = True
    downloader.start()

    # Process metadata in batches in the main thread
    current_batch = []
    papers_processed = 0

    while True:
        # Get next metadata item
        paper_data = metadata_queue.get()

        # Check for end sentinel
        if paper_data is END_SENTINEL:
            break

        # Add to current batch
        current_batch.append(paper_data)

        # Process batch if it's full
        if len(current_batch) >= batch_size:
            process_batch(current_batch)
            papers_processed += len(current_batch)
            print(f"Total papers processed so far: {papers_processed}/{len(papers_metadata)}")
            current_batch = []

    # Process any remaining items
    if current_batch:
        process_batch(current_batch)
        papers_processed += len(current_batch)
        print(f"Total papers processed: {papers_processed}/{len(papers_metadata)}")

    print(f"Dataset generation complete. Results saved to {dataset_path}")

# Call the function to generate the dataset
if __name__ == "__main__":
    generate_dataset()
