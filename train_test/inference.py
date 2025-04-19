from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained("unsloth/Llama-3.2-3B-Instruct")
tokenizer = AutoTokenizer.from_pretrained("unsloth/Llama-3.2-3B-Instruct")
