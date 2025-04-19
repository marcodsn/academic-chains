import os
import json
from dotenv import load_dotenv
from typing import List
from pydantic import BaseModel, Field
from random import shuffle
from together import Together

from docling.document_converter import DocumentConverter
from transformers import AutoTokenizer

# Initialize Together AI client
load_dotenv()
api_key = os.getenv("TOGETHER_API_KEY")
if api_key is None:
    raise ValueError("TOGETHER_API_KEY environment variable not set")
together = Together(api_key=api_key)

model = "deepseek-ai/DeepSeek-V3"

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

def generate_dataset():
    dataset_path = "dataset/data/train.jsonl"

    # Ensure directory exists
    os.makedirs(os.path.dirname(dataset_path), exist_ok=True)

    for paper in papers_metadata:
        try:
            print(f"Processing paper {paper.get('arxiv_id', 'unknown')}...")
            paper_doc = converter.convert(paper["pdf_url"])
            paper_md = paper_doc.document.export_to_markdown()

            # Create prompts for this paper
            prompt_multi_short = prompts["multi-short"].replace("{paper_3}", paper_md)
            prompt_single_long = prompts["single-long"].replace("{paper_3}", paper_md)

            # Multi-short entry using structured output
            try:
                response_multi_short = together.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful assistant. Only answer in JSON format."
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
                    }
                )

                # Get the structured data
                multi_short_content = response_multi_short.choices[0].message.content
                multi_short_data = json.loads(multi_short_content)

                # Calculate average thinking tokens
                avg_thinking_tokens = 0
                assistant_replies = 0

                for entry in multi_short_data["conversations"]:
                    if entry["role"] == "assistant":
                        assistant_replies += 1
                        # Extract thinking section between <think> tags
                        try:
                            think_content = entry["content"].split("<think>")[1].split("</think>")[0].strip()
                            avg_thinking_tokens += len(tokenizer.tokenize(think_content))
                        except IndexError:
                            print("Warning: Could not find <think>...</think> tags in assistant message")

                if assistant_replies > 0:
                    avg_thinking_tokens /= assistant_replies
                else:
                    avg_thinking_tokens = 0

                multi_short_data_dict = multi_short_data["conversations"]

            except Exception as e:
                print(f"Error with multi-short API call: {e}")
                multi_short_data_dict = []
                avg_thinking_tokens = 0

            multi_short_entry = {
                "arxiv_id": paper.get("arxiv_id", ""),
                "paper_doi": paper.get("doi", ""),
                "paper_authors": paper.get("authors", []),
                "paper_published_date": paper.get("published_date", ""),
                "paper_updated_date": paper.get("updated_date", ""),
                "conversations": multi_short_data_dict,
                "entry_type": "multi-short",
                "categories": paper.get("categories", []),
                "avg_thinking_tokens": avg_thinking_tokens,
                "model": model
            }

            # Single-long entry using structured output
            try:
                response_single_long = together.chat.completions.create(
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
                )

                # Get the structured data
                single_long_content = response_single_long.choices[0].message.content
                single_long_data = json.loads(single_long_content)

                # Calculate average thinking tokens
                avg_thinking_tokens = 0
                assistant_replies = 0

                for entry in single_long_data["conversations"]:
                    if entry["role"] == "assistant":
                        assistant_replies += 1
                        # Extract thinking section between <think> tags
                        try:
                            think_content = entry["content"].split("<think>")[1].split("</think>")[0].strip()
                            avg_thinking_tokens += len(tokenizer.tokenize(think_content))
                        except IndexError:
                            print("Warning: Could not find <think>...</think> tags in assistant message")

                if assistant_replies > 0:
                    avg_thinking_tokens /= assistant_replies
                else:
                    avg_thinking_tokens = 0

                single_long_data_dict = single_long_data["conversations"]

            except Exception as e:
                print(f"Error with single-long API call: {e}")
                single_long_data_dict = []
                avg_thinking_tokens = 0

            single_long_entry = {
                "arxiv_id": paper.get("arxiv_id", ""),
                "paper_doi": paper.get("doi", ""),
                "paper_authors": paper.get("authors", []),
                "paper_published_date": paper.get("published_date", ""),
                "paper_updated_date": paper.get("updated_date", ""),
                "conversations": single_long_data_dict,
                "entry_type": "single-long",
                "categories": paper.get("categories", []),
                "avg_thinking_tokens": avg_thinking_tokens,
                "model": model
            }

            with open(dataset_path, "a") as f:
                f.write(json.dumps(multi_short_entry) + "\n")
                f.write(json.dumps(single_long_entry) + "\n")

            print(f"Successfully processed paper {paper['arxiv_id']}")

        except Exception as e:
            print(f"Error processing paper {paper.get('arxiv_id', 'unknown')}: {e}")

# Call the function to generate the dataset
if __name__ == "__main__":
    generate_dataset()
