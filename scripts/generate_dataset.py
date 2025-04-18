import os
import json
from docling.document_converter import DocumentConverter
from openai import OpenAI

# Initialize Gemini's API client
client = OpenAI(
    api_key="AIzaSyCjBZe6iBBeR3LHavbW2jti1EYytIwJ_iI",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

# response = client.chat.completions.create(
#     model="gemini-2.5-flash-preview-04-17",
#     n=1,
#     messages=[
#         {"role": "system", "content": "You are a helpful assistant."},
#         {
#             "role": "user",
#             "content": "Explain to me how AI works"
#         }
#     ]
# )

# print(response.choices[0].message.content)

# Loading papers metadata
papers_metadata = []
with open("data/arxiv_metadata.jsonl", "r") as f:
    for line in f:
        papers_metadata.append(json.loads(line))

# Loading prompts
prompts = {}
with open("prompts/extraction_examples.jsonl", "r") as f:
    prompts["multi-short"] = f.read()
with open("prompts/long_extraction_examples.jsonl", "r") as f:
    prompts["single-long"] = f.read()

with open("prompts/example_papers/paper_1.md", "r") as f:
    prompts["multi-short"].replace("{paper_1}", f.read())
    prompts["single-long"].replace("{paper_1}", f.read())

with open("prompts/example_papers/paper_2.md", "r") as f:
    prompts["multi-short"].replace("{paper_2}", f.read())
    prompts["single-long"].replace("{paper_2}", f.read())

# Defining functions
converter = DocumentConverter()

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

            # System prompt instructing the model to return JSON
            system_prompt = "You are a helpful assistant. Format your answer as a JSON object with a 'conversations' array. The exact format should be: {\"conversations\": [...]} with all extracted information inside this structure."

            # Multi-short entry
            try:
                answer_multi_short = client.chat.completions.create(
                    model="gemini-2.5-flash-preview-04-17",
                    n=1,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt_multi_short}
                    ]
                )

                multi_short_response = answer_multi_short.choices[0].message.content

                # Format the response
                multi_short_response = multi_short_response.strip()
                if "```json" in multi_short_response:
                    multi_short_response = multi_short_response.split("```json")[1].split("```")[0].strip()

            except Exception as e:
                print(f"Error with multi-short API call: {e}")
                multi_short_response = "{\"conversations\": []}"

            multi_short_entry = {
                "arxiv_id": paper.get("arxiv_id", ""),
                "paper_doi": paper.get("doi", ""),
                "paper_authors": paper.get("authors", []),
                "paper_pdate": paper.get("published_date", ""),
                "paper_udate": paper.get("updated_date", ""),
                "conversations": multi_short_response,
                "entry_type": "multi-short",
                "categories": paper.get("categories", []),
                "model": "gemini-2.5-flash-preview-04-17"
            }

            # Single-long entry
            try:
                answer_single_long = client.chat.completions.create(
                    model="gemini-2.5-flash-preview-04-17",
                    n=1,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt_single_long}
                    ]
                )

                single_long_response = answer_single_long.choices[0].message.content

                # Format the response
                single_long_response = single_long_response.strip()
                if "```json" in single_long_response:
                    single_long_response = single_long_response.split("```json")[1].split("```")[0].strip()

            except Exception as e:
                print(f"Error with single-long API call: {e}")
                single_long_response = "{\"conversations\": []}"

            single_long_entry = {
                "arxiv_id": paper.get("arxiv_id", ""),
                "paper_doi": paper.get("doi", ""),
                "paper_authors": paper.get("authors", []),
                "paper_pdate": paper.get("published_date", ""),
                "paper_udate": paper.get("updated_date", ""),
                "conversations": single_long_response,
                "entry_type": "single-long",
                "categories": paper.get("categories", []),
                "model": "gemini-2.5-flash-preview-04-17"
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
