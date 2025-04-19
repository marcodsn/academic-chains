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
dataset_info:
  features:
    - name: arxiv_id
      dtype: string
    - name: paper_doi
      dtype: string
    - name: paper_authors
      dtype: list[string]
    - name: paper_published_date
      dtype: string
    - name: paper_updated_date
      dtype: string
    - name: conversations
      dtype: list[dict]
    - name: entry_type
      dtype: string  # multi-short, single-long
    - name: categories
      dtype: list[string]
    - name: avg_thinking_tokens
      dtype: float
    - name: model
      dtype: string
  splits:
    - name: train
      num_bytes: # Fill this in after creation
      num_examples: # Fill this in after creation (should be >= 100 for competition)
      download_size: # Fill this in
      dataset_size: # Fill this in
---

# Dataset Card for Academic Reasoning and Intuition Chains

## Dataset Description

*   **GitHub (dataset generation code):** [Link to your GitHub repo if you create one]
*   **Dataset (this page):** [Link to the Hugging Face dataset repo after upload]

This dataset contains reasoning chains distilled from open-access research papers, primarily focusing on the q-bio and econ.GN categories (check [arXiv](https://arxiv.org) for more information on the categories). The goal is to create grounded reasoning chains that capture the underlying logical structure, argumentation, or justification presented by the authors.

This dataset was created as a proof-of-concept for the Reasoning Datasets Competition (April 2025).

## Dataset Creation

### Source Data

The reasoning chains were derived from text extracted from open-access research papers sourced from [arXiv](https://arxiv.org). Papers were selected from the fields of Quantitative Biology (q-bio) and General Economics (econ.GN), but new fields may also be considered in the future.

### Data Collection and Processing

The creation pipeline involved the following steps:

1.  **Metadata Gathering:** We used the `arxiv` python API wrapper to fetch metadata for papers from the fields of Quantitative Biology (q-bio) and General Economics (econ.GN), filtering by Relevance.
2.  **PDF Text Extraction:** Text was then extracted from source PDFs using the `docling` library, in markdown format.
3.  **Reasoning Chain Extraction:** An LLM (for this demo, we used `gemini-2.5-flash-preview-04-17` and `gemini-2.5-pro-exp-03-25`) was prompted, using few-shot examples with curated paper-to-reasoning samples, to extract the reasoning chain/s from the selected papers.
4.  **Formatting and Cleaning:** The final dataset entries have been filtered (removed entries with no reasoning chains) and formatted into a standardized JSON structure; each entry also cites the source paper and its authors, and includes the average length of the reasoning chains in the specific entry, useful for training of approximated reasoning-with-budget-of-n models.

**Note on step 2:** From the same paper, we extract: multiple shorter reasoning chains (type: "multi-short" in the dataset) and a single, longer reasoning chain (type: "single-long" in the dataset) which tries to capture the main BIG question-reasoning-answer triplet of the paper.

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

## Example Uses and Preliminary Evaluation

This dataset can be used to train multi-domain reasoning models. Specifically, we fine-tuned [unsloth/Llama-3.2-3B-Instruct](https://huggingface.co/unsloth/Llama-3.2-3B-Instruct) using the [unsloth](https://unsloth.ai/) library (you can find more details and code on [GitHub](https://github.com/marcodsn/reasoning-dataset-competition/tree/main/train_test)); here we provide WIP evaluation metrics and results:

# MMLU-Pro



## Limitations and Biases

*   **Source Bias:** The dataset reflects the topics, writing styles, and potential biases present in the selected open-access papers. Fields or regions with less open-access publishing may be underrepresented.
*   **Extraction Fidelity:** LLM extraction can introduce errors (hallucination, misinterpretation) even when grounding the reasoning chains with the original text (hallucinations still exist in RAG, so it comes out naturally that they will also be present in our reasoning chains).
*   **Limited Scope:** This proof-of-concept dataset contains <=1000 examples and may not cover the full breadth of reasoning patterns even within the selected domains; we will try to expand it in the future!

## Licensing Information

This dataset is licensed under the [Apache License 2.0].

## Citation Information


@misc{marcodsn_2025_academicchains,
author = {[Marco De Santis]},
title = {Academic Reasoning Chains Dataset},
year = {2025},
publisher = {Hugging Face},
url = {[Link to dataset on Hugging Face Hub]}
}
