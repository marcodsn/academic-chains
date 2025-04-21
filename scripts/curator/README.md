# Notes on Curator use

## The Problem!

As you may have noticed, the original academic-chains dataset's generation pipeline is not really suited for adopting [Bespoke Curator](https://github.com/bespokelabsai/curator). Up until now, my code:
- Downloaded the paper's pdf
- Extracted the text from the pdf
- Ran inference on the prompt with the extracted text

These steps all happened one after another, with no parallelism, and no pre-processed seed dataset.

## Optimization Approaches

To optimize the pipeline and to adapt it to Curator, I had to get a little creative with my approach; the alternatives that came to mind were:

1. **Pre-processing Option**: Pre-downloading & pre-processing the papers to get the texts, and then use Curator on this "seed dataset".
2. **Batch Processing Option**: Implementing background batch processing to still leverage Curator while not re-implementing the entire pipeline (also good for fast prototyping).

## Implemented Solution

I chose option 2: I kept the original pipeline, but I modified it to work in batches so that I can still leverage Curator's easy-to-use batched inference capabilities for cost savings!

> Yes, it's not the optimal solution, and for a large-scale generation run I will probably move to option 1, but this works well enough for a proof-of-concept I think :).

### Performance Gains

These new scripts are also MUCH faster than what I had before, as I also implemented a prepare-ahead strategy and currently the only bottleneck is the inference speed itself (before each inference step had to wait for the new pdf to be downloaded and processed... Yes I know, my fault, I could have optimized that from the start!).
