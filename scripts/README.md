# Notes on Curator use

## The Problem!

As you may have noticed, the original academic-chains dataset's generation pipeline was not really suited for adopting [Bespoke Curator](https://github.com/bespokelabsai/curator). Up until now, my code:
- Downloaded the paper's pdf
- Extracted the text from the pdf
- Ran inference on the prompt with the extracted text

These steps all happened one after another, with no parallelism, and no pre-processed seed dataset.

## Optimization Approaches

To optimize the pipeline and to adapt it to Curator, I considered two approaches:

1. **Pre-processing Option**: Pre-downloading & pre-processing the papers to get the texts, and then use Curator on this "seed dataset".
2. **Batch Processing Option**: Implementing background batch processing to still leverage Curator while not re-implementing the entire pipeline.

## Implemented Solution: From Batch Processing to Pre-processed Dataset

Initially, I implemented option 2 (batch processing) as a quick proof-of-concept to leverage Curator's batched inference capabilities.

**However, we've now created a much better solution!** We've built a comprehensive pre-processed dataset at [marcodsn/arxiv-markdown](https://huggingface.co/datasets/marcodsn/arxiv-markdown) containing arXiv papers already converted to markdown format.

This represents a full transition to option 1 (pre-processing), bringing several advantages:
- **Eliminates PDF processing overhead**: No more waiting for downloads and extraction
- **Maximizes Curator efficiency**: Full focus on inference without bottlenecks
- **Better markdown quality**: Using docling for high-quality conversion with formula and code enrichment
- **Image support**: All figures are preserved as external image URLs
- **Faster iterations**: Allows rapid experimentation with different prompts and models

### Performance Gains

With this pre-processed dataset, the pipeline is now significantly faster since the only bottleneck is the inference speed itself. We've eliminated all the PDF downloading and processing steps that previously created delays between inference steps.

This approach is much more scalable and is the recommended path for anyone looking to generate large volumes of academic content with Curator!


## Notes for myself (will be made easier at release time)
pipeline:
- generate data (generates zraw.jsonl)
- deduplicate
- process (generates zprocessed.jsonl)
- verify (generates zverified*.jsonl files)
- merge verifiers (generates train.jsonl)
