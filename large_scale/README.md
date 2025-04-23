# THE PLAN

Ok so, very rough and definitely not definitive pipeline:
1. We are going to extract markdowns from arxiv papers ahead of time (currently we are doing one month at a time); images will be saved as embedded base64 data (for a possible future multimodal dataset) inside the markdown, formulas converted in latex (many thanks to [docling](https://github.com/docling-project/docling/tree/main))
2. We are going to clean this data and to upload it regurarly to the [Hub](https://huggingface.co/) under [`marcodsn/arxiv-markdown`](https://huggingface.co/datasets/marcodsn/arxiv-markdown) (for simplicity)
3. This data will be used to create the prompts to be sent to the LLM inference engine (we will leverage [Curator](https://github.com/bespokelabsai/curator) for easy batched inferenced and monitoring)
4. As in the old pipeline, we will clean the data by removing non-valid examples, although... (check the line below 👀)

**BONUS:** We are going add a model-in-the-loop validation system! The idea is to have a small model fine-tuned on checking problems like: does this data entry mention a "text" or "paper"? (it shall not by design, but we noticed that some data entries do that mistake!)

**Note:** Because of a [known bug in docling](https://github.com/docling-project/docling/issues/1283), we currently use a timeout of 240 seconds per element in the batch for the extractor script (we work with small batches of 4); because of this reason, some papers may get skipped and not appear in the dataset, but as the quantity of available data is not a problem (as we are currently extracting 2024 data, we see something like 25k papers published every month) we believe this tradeoff is ok for now.
