from docling.document_converter import DocumentConverter

paper = "https://arxiv.org/pdf/nlin/0303057"

converter = DocumentConverter()
doc = converter.convert(paper)
doc.document.save_as_markdown("prompts/example_papers/paper_3.md")
