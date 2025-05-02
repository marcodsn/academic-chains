# Academic Reasoning and Intuition Chains

![Surgeon problem solved lol](surgeon-competition-dark.png)

A high-quality dataset of reasoning and intuition chains distilled from open-access research papers-primarily in quantitative biology, general economics, and related STEM fields. This project demonstrates a modern pipeline for extracting, verifying, and packaging research-like reasoning, developed for the [Reasoning Datasets Competition (April 2025)](https://huggingface.co/blog/bespokelabs/reasoning-datasets-competition).

- **HuggingFace Dataset:** [marcodsn/academic-chains](https://huggingface.co/datasets/marcodsn/academic-chains)
- **GitHub Repository:** [marcodsn/academic-chains](https://github.com/marcodsn/academic-chains)

---

## Overview

This repository contains code, data, and documentation for building and evaluating *academically-grounded reasoning chains*-aiming to capture not just logical steps, but also the hypothesis-driven, intuitive, and exploratory thinking central to scientific research. Our focus is on creating data that emulates how researchers reason about problems *before* outcomes are known.

---

## Table of Contents

- [Repository Structure](#repository-structure)
- [Installation](#installation)
- [Dataset Creation Pipeline](#dataset-creation-pipeline)
- [Dataset Structure](#dataset-structure)
- [Usage and Evaluation](#usage-and-evaluation)
- [Quality Control and Verification](#quality-control-and-verification)
- [Known Limitations & Biases](#known-limitations--biases)
- [Development Roadmap](#development-roadmap)
- [Acknowledgements](#acknowledgements)
- [License](#license)
- [Citation](#citation)

---

## Repository Structure

```
academic-chains/
├── data/
│   ├── checkpoints/        # Intermediate pipeline states
│   ├── jsonls/             # Inputs/outputs for data generation & verification
│   └── *.png               # Figures and example images
├── prompts/                # LLM prompts and few-shot examples
│   ├── example_papers/
│   ├── extraction_examples.txt
│   ├── long_extraction_examples.txt
│   └── verifier.txt
├── scripts/                # Creation, processing, and verification scripts
│   ├── data_generation/
│   │   ├── curator_cohere.py
│   │   ├── curator_gemini.py
│   │   ├── curator_ollama.py
│   │   ├── curator_togetherai.py
│   │   └── togetherai.py
│   ├── data_processing/
│   │   ├── deduplicate.py
│   │   ├── process.py
│   │   ├── verify_dataset.py
│   │   └── merge_verifiers.py
│   ├── generate_reqs.sh
│   ├── upload_to_hf.py
│   └── README.md
└── src/                    # Evaluation & (planned) training scripts
```

---

## Installation

```bash
git clone https://github.com/marcodsn/academic-chains.git
cd academic-chains
pip install -r requirements.txt
```

---

## Dataset Creation Pipeline

Our state-of-the-art pipeline (see `scripts/curator_*` and [Bespoke Curator](https://github.com/bespokelabsai/curator/)) involves:

1. **Metadata Gathering:** Paper metadata sourced via the arXiv API, focusing on q-bio, econ.GN, and an expanding set of STEM domains.
2. **PDF Text Extraction:** Using the [`arxiv-markdown`](https://github.com/marcodsn/arxiv-markdown) pipeline, we extract clean Markdown from paper PDFs.
3. **Reasoning & Intuition Chain Generation:** LLMs (e.g., Gemini 2.5, DeepSeek-V3, Llama-4-Maverick) are prompted with few-shot examples to produce research-style chains.
    - Short forms (`entry_type: multi-short`) and longer, main-question chains (`entry_type: single-long`) are both included.
4. **Automated Filtering:** Removes formatting errors, off-topic or incomplete generations, and misaligned responses.
5. **LLM-Based Verification:** Multiple LLM "verifiers" (Qwen3, Mistral, Gemma) label each chain as "Suitable" (truly hypothetical or conceptual) or "Unsuitable" (merely reporting results), with justifications and agreement scores.
6. **Final Packaging:** All metadata, chains, and verification results are structured in standardized JSONL.

---

## Dataset Structure

Each example includes:

- `arxiv_id`, `paper_doi`, `paper_authors`, `paper_published_date`, `paper_updated_date`
- `conversations`: List of role/content dicts (ChatML format), typically user prompt + assistant reasoning (`<think>` ... `</think>`)
- `entry_type`: "multi-short" or "single-long"
- `categories`: Academic domains (e.g., `q-bio.PE`, `econ.GN`)
- `avg_thinking_tokens`: Reasoning "budget" for the thought section
- `model`: LLM used for that chain
- `verifier_results`: Per-verifier judgments (with justifications and model names)
- `suitability_score`: Normalized (0–1) agreement across verifiers
- `suitability`: Final "Suitable" or "Unsuitable" label

**For more, see [our HuggingFace dataset card](https://huggingface.co/datasets/marcodsn/academic-chains).**

---

## Usage and Evaluation

- Run dataset generation:
  `python scripts/data_generation/curator_gemini.py`
- Process/deduplicate results:
  `python scripts/data_processing/process.py`
- Quality control (verification):
  `python scripts/data_processing/verify_dataset.py`
- Fine-tune models (planned):
  See `src/train/train.py` (WIP)

The dataset is designed to facilitate research and development of models with explicit, controllable scientific reasoning skills-chain-of-thought, intuition, and hypothesis formation.

---

## Quality Control and Verification

**Why is this dataset different?**
- We *actively* filter out result-reporting using an ensemble of LLM verifiers, raising the bar for true hypothetical/researcher-style reasoning.
- Detailed metadata, multi-stage pipeline, and agreement metrics are included for transparency and downstream filtering.
- The pipeline is fully open-[prompt examples](./prompts), [verifier code](./scripts/data_processing/verify_dataset.py), and more.

---

## Known Limitations & Biases

- **Source Bias:** Mirrors the domains and style of open-access arXiv papers (q-bio, econ.GN, etc.), with some fields underrepresented.
- **Extraction Fidelity:** LLMs, even when prompted for hypothetical reasoning, can stray or hallucinate; multi-verifier QC mitigates but doesn't eliminate this.
- **Scope & Size:** As of April/May 2025, <2,000 post-QC examples; ongoing scaling planned.
- **Definition Subjectivity:** What counts as "researcher intuition" vs. "result reporting" is imperfect-even for LLM verifiers.

---

## Development Roadmap

- Expanded domain and data volume (more fields beyond STEM)
- Enhanced verification (human-in-the-loop, more rigorous prompt tuning)
- Multi-modal reasoning chains: incorporating figures, equations, etc.
- Incorporate community feedback & support new benchmarks

Development branch: [`dev`](https://github.com/marcodsn/academic-chains/tree/dev) (to be released)

---

## Acknowledgements

Huge thanks to my team at [Noetic Labs](https://huggingface.co/NoeticLabs) for their support! Massive appreciation to [HuggingFace](https://huggingface.co/), [Bespoke Labs](https://www.bespokelabs.ai/), and [Together AI](https://together.ai/) for organizing this competition and fostering innovation in reasoning datasets. And most importantly, profound gratitude to the Academic Community and the authors of countless open-access papers – your work makes projects like this possible. THANK YOU!

---

## License

Distributed under the Apache License 2.0. See [LICENSE](LICENSE).

---

## Citation

```bibtex
@misc{marcodsn_2025_academicchains,
    title = {Academic Reasoning and Intuition Chains Dataset},
    author = {Marco De Santis},
    month = {April},
    year = {2025},
    url = {https://huggingface.co/datasets/marcodsn/academic-chains}
}
```

---
