import os

DATASET_DIR = "data/jsonls"
CHECKPOINTS_DIR = "data"

def deduplicate(lines):
    return list(set(lines))

# Deduplicate dataset
files_in_dir = os.listdir(DATASET_DIR)
for file in files_in_dir:
    if file.endswith(".jsonl"):
        lines = []
        with open(os.path.join(DATASET_DIR, file), "r") as f:
            lines.extend(f.readlines())

        lines = deduplicate(lines)
        pre_deduped_lines = len(lines)

        # file = file.replace(".jsonl", ".deduped.jsonl")
        with open(os.path.join(DATASET_DIR, file), "w") as f:
            f.writelines(lines)

        print(f"{file}: {pre_deduped_lines} -> {len(lines)}")

# Deduplicate checkpoints
files_in_dir = os.listdir(CHECKPOINTS_DIR)
for file in files_in_dir:
    if file.startswith(".checkpoint"):
        lines = []
        with open(os.path.join(CHECKPOINTS_DIR, file), "r") as f:
            lines.extend(f.readlines())

        lines = deduplicate(lines)
        pre_deduped_lines = len(lines)

        # file = file.replace(".jsonl", ".deduped.jsonl")
        with open(os.path.join(CHECKPOINTS_DIR, file), "w") as f:
            f.writelines(lines)

        print(f"{file}: {pre_deduped_lines} -> {len(lines)}")
