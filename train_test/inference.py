from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained("unsloth/Llama-3.2-8B-Instruct")
tokenizer = AutoTokenizer.from_pretrained("unsloth/Llama-3.2-8B-Instruct")
