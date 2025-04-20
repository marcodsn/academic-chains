---
tags:
- reasoning-datasets-competition # Competition tag!
- reasoning
- academic-papers
- question-answering
- chain-of-thought
- biology
- economics
language:
- en
license: apache-2.0
pretty_name: "Academic Reasoning and Intuition Chains"
configs:
  - config_name: default
    data_files:
      - split: train
        path: "data/train.jsonl"
      - split: zraw
        path: "data/zraw.jsonl"
---

# Dataset Card for Academic Reasoning and Intuition Chains

## Dataset Description

*   **GitHub:** [https://github.com/marcodsn/reasoning-dataset-competition](https://github.com/marcodsn/reasoning-dataset-competition)
*   **Dataset:** [https://huggingface.co/datasets/marcodsn/academic-chains](https://huggingface.co/datasets/marcodsn/academic-chains) (this page)

This dataset contains reasoning chains distilled from open-access research papers, primarily focusing on the q-bio and econ.GN categories (check [arXiv](https://arxiv.org) for more information about the categories). The goal is to create academically-grounded reasoning chains that capture the underlying logical structure, argumentation, or justification presented by the authors.

This dataset was created as a proof-of-concept for the Reasoning Datasets Competition (April 2025).

## Dataset Creation

### Source Data

The reasoning chains were derived from text extracted from open-access research papers sourced from [arXiv](https://arxiv.org). Papers were selected from the fields of Quantitative Biology (q-bio) and General Economics (econ.GN), but new fields may (and most probably will) be considered in the future.

### Data Collection and Processing

The creation pipeline involved the following steps:

1.  **Metadata Gathering:** We used the `arxiv` python API wrapper to fetch metadata for papers from the fields of Quantitative Biology (q-bio) and General Economics (econ.GN), filtering by Relevance.
2.  **PDF Text Extraction:** Text was then extracted from source PDFs using the `docling` library, in markdown format.
3.  **Reasoning Chain Extraction:** An LLM (for this demo, we used `gemini-2.5-flash-preview-04-17`, `gemini-2.5-pro-exp-03-25`, and `deepseek-ai/DeepSeek-V3`) was prompted, using few-shot examples with curated paper-to-reasoning samples, to extract the reasoning chain/s from the selected papers.
4.  **Formatting and Cleaning:** The final dataset entries have been filtered (removed entries with no reasoning chains) and formatted into a standardized JSON structure; each entry also cites the source paper and its authors, and includes the average length of the reasoning chains in the specific entry, useful for training of approximated reasoning-with-budget-of-n models.

**Notes on step 3:** From the same paper, we extract: multiple shorter reasoning chains (entry_type: "multi-short" in the dataset) and a single, longer reasoning chain (entry_type: "single-long" in the dataset) which tries to capture the main BIG question-reasoning-answer triplet of the paper.

The code used to generate this dataset is available on our [reasoning-datasets-competition](https://github.com/marcodsn/reasoning-datasets-competition) repository.

### Dataset Structure

Each example in the dataset includes:
*   `arxiv_id`: Identifier for the source paper.
*   `paper_doi`: DOI or URL link to the original paper.
*   `paper_authors`: List of authors of the paper.
*   `paper_published_date`: Date of publication of the paper.
*   `paper_updated_date`: Date of last update of the paper.
*   `conversations`: List of dictionaries containing the reasoning chain in a conversational format. Each entry includes:
    *   `user`: The question or prompt about the paper content.
    *   `assistant`: The response providing reasoning or explanation.
*   `entry_type`: Indicates whether the entry contains multiple short reasoning chains or a single long chain.
*   `categories`: List of academic categories or subfields the paper belongs to.
*   `avg_thinking_tokens`: Average number of tokens in the thinking sections, indicating reasoning complexity.
*   `model`: The LLM used to generate the reasoning chains.

## Example Uses

This dataset can be used to train multi-domain reasoning models with a specified approximated budget of thinking tokens, in a similar way to how `Gemini 2.5` and `Claude Sonnet 3.7` allow API users to choose a thinking budget too.

**Notes:** Our intuition says that mixing this reasoning dataset with non-reasoning datasets focused on instruction following may lead to even better results overall; we will test this theory ASAP.

# Preliminary Evaluation

We tested and fine-tuned [unsloth/Llama-3.2-3B-Instruct](https://huggingface.co/unsloth/Llama-3.2-3B-Instruct) (the bnb-4bit version was used for efficient tuning) using LoRA with the [unsloth](https://unsloth.ai/) library (you can find more details and code on [GitHub](https://github.com/marcodsn/reasoning-dataset-competition/tree/main/train_test)); here we provide (very) WIP evaluation results:

## MMLU-Pro

| Model                                   | Economics |
| --------------------------------------- | --------- |
| Llama-3.2-3B-Instruct (baseline)        | 22.5%     |
| Llama-3.2-3B-Instruct + Academic Chains | 29.7%     |
| Improvement                             | +7.2%     |

**Note 1:** While fine-tuning, we used the following system prompt: f"You are a helpful assistant. Think before answering and put your thoughts between the \<think> and \</think> tags. Your thinking budget for this conversation is {avg_thinking_tokens} tokens.", where "avg_thinking_tokens" is the avg_thinking_tokens value for the current example.

**Note 2:** The system prompt used for testing our fine-tuned model is "You are a helpful assistant. Think before answering and put your thoughts between the \<think> and \</think> tags. Your thinking budget for this conversation is 256 tokens."

**Note 3:** Yes, we are aware that our results are lower than expected *for both models*; the problem likely stems from the use of llama.cpp as the server to host these models (we quantized them to q8). If time allows, we will run the tests again loading the fp16 versions in the Transformers library directly.

## Example Output

![Example Model Output](reasoning-competition-dark.png)

We also fine-tuned [unsloth/Qwen2.5-7B-Instruct](https://huggingface.co/unsloth/Qwen2.5-7B-Instruct) (same library and similar code have been used); results for this model will be uploaded soon™️.

# Scaling Plan

Our scaling plan includes:
1. **Expanded Domain Coverage:** Extend beyond q-bio and econ.GN to include additional scientific fields such as Computer Science (cs.AI, cs.CL), Physics (physics), and more categories too (Social Sciences?).
2. **Increased Volume:** Scale from our current proof-of-concept size to LOTS+ reasoning chains (if/when compute allows)
3. **Enhanced Quality Verification:** We would also try and implement a model-in-the-loop validation system to check for hallucinations, bad instruction following samples and low quality reasoning chains
4. **Multi-modal Reasoning:** Extend our approach to extract reasoning from papers that include charts, diagrams, and mathematical formulations (gemma-3 as the base model anyone? 👀)

## Limitations and Biases

*   **Source Bias:** The dataset reflects the topics, writing styles, and potential biases present in the selected open-access papers. Fields or regions with less open-access publishing may be underrepresented.
*   **Extraction Fidelity:** LLM extraction can introduce errors (hallucination, misinterpretation) even when grounding the reasoning chains with the original text (hallucinations still exist in RAG, so it comes out naturally that they will also be present in our reasoning chains).
*   **Limited Scope:** This proof-of-concept dataset contains <1000 examples and may not cover the full breadth of reasoning patterns even within the selected domains; we will work on expanding it in the future!

## Licensing Information

This dataset is licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0.txt).

## Citation Information

```
@misc{marcodsn_2025_academicchains,
	title = {Academic Reasoning and Intuition Chains Dataset},
	author = {Marco De Santis},
	month = {April},
	year = {2025},
	url = {https://huggingface.co/datasets/marcodsn/academic-chains}
}
```
