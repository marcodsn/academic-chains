OLD_RAWS=["./data/jsonls_direct_api/zraw_direct_meta-llama_Llama-4-Maverick-17B-128E-Instruct-FP8.jsonl"]
NEW_RAW="./data/jsonls/zraw_curator.jsonl"

# Append old data to new data and save as new data
def append_old_data_to_new_data():
    with open(NEW_RAW, 'a') as new_raw_file:
        for old_raw in OLD_RAWS:
            with open(old_raw, 'r') as old_raw_file:
                for line in old_raw_file:
                    new_raw_file.write(line)

append_old_data_to_new_data()
