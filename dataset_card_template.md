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
      dtype: string # multi-short, single-long # multi-short, single-long
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

*   **Homepage:** [Link to your GitHub repo if you create one]
*   **Repository:** [Link to the Hugging Face dataset repo after upload]
*   **Point of Contact:** [Your Name/Email/HF Username]

This dataset contains reasoning chains distilled from text segments of academic research papers, primarily focusing on [mention your chosen subfields like Molecular Biology, Sociology, etc.]. The goal is to capture the underlying logical structure, argumentation, or justification presented by the authors.

This dataset was created as a proof-of-concept for the Reasoning Datasets Competition (April-May 2025).

## Dataset Creation

### Source Data

The reasoning chains were derived from text segments extracted from open-access research papers sourced from [mention sources like arXiv, PubMed Central, etc.]. Papers were selected from the fields of [mention domains].

### Data Collection and Processing

The creation pipeline involved the following steps:

1.  **PDF Text Extraction:** Text was extracted from source PDFs using the `docling` library. Segments relevant for reasoning (e.g., Abstracts, Introduction paragraphs, Discussion paragraphs) were prioritized where possible.
2.  **Reasoning Potential Evaluation:** Text segments were evaluated for their likelihood of containing extractable reasoning chains using an LLM (`[Specify OpenAI model used, e.g., gpt-3.5-turbo]`). This evaluation included a numerical score and a textual justification, guided by few-shot examples (`prompts/evaluation_examples.jsonl`). Segments scoring above `[Your Threshold]` were selected.
3.  **Reasoning Chain Extraction:** An LLM (`[Specify OpenAI model used, e.g., gpt-4-turbo]`) was prompted, using few-shot examples (`prompts/extraction_examples.jsonl`), to extract the reasoning chain from the selected high-potential text segments.
4.  **Manual Curation:** The raw extracted chains underwent manual review and refinement to ensure accuracy, logical coherence, fidelity to the source text, and consistent formatting. This step was crucial for dataset quality.

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

This dataset can be used to train or evaluate models on tasks such as:

*   Understanding complex argumentation in academic writing.
*   Distilling core logic from dense text.
*   Generating summaries focused on reasoning steps.
*   Evaluating the reasoning capabilities of LLMs on specialized domains.
*   Training smaller models to follow complex reasoning patterns.

## Limitations and Biases

*   **Source Bias:** The dataset reflects the topics, writing styles, and potential biases present in the selected open-access papers. Fields or regions with less open-access publishing may be underrepresented.
*   **Extraction Fidelity:** While manually curated, the distilled chains are interpretations of the source text and may not capture every nuance. LLM extraction can introduce errors (hallucination, misinterpretation) that curation aimed to minimize but might not entirely eliminate.
*   **Text Extraction Quality:** PDF text extraction can be imperfect, potentially affecting the quality of the `source_text_segment`.
*   **Limited Scope:** This proof-of-concept dataset contains >=100 examples and may not cover the full breadth of reasoning patterns even within the selected domains.

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
