#!/usr/bin/env python3
"""
Merge all verification results from multiple verifier models.
This script finds all model-specific output files and merges them into a single file.
"""

import os
import json
import glob
import argparse
import uuid
from typing import Dict
from collections import defaultdict
import time

# Default paths
DEFAULT_OUTPUT_DIR = "data/jsonls"
DEFAULT_MERGED_OUTPUT = "data/jsonls/zverified.jsonl"
DEFAULT_FILE_PATTERN = "zverified_*.jsonl"

def generate_content_id(conversations):
    """Generate a deterministic UUID based on the content of conversations"""
    if conversations is None:
        return str(uuid.uuid4())  # Random UUID if no conversations

    # Convert conversations to a string and encode it
    conv_str = json.dumps(conversations, sort_keys=True)
    # Create a UUID5 using the DNS namespace and the conversation string
    content_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, conv_str))
    return content_id

def extract_model_name(filename: str) -> str:
    """Extract the model name from the filename."""
    # Pattern: zverified_modelname.jsonl
    name = filename.split(".jsonl")[0].replace("zverified_", "")
    return name

def calculate_agreement_rates(merged_data):
    """Calculate the agreement rates between verifier models."""
    # Get all verifier models
    all_verifiers = set()
    for item in merged_data.values():
        for result in item.get("verifier_results", []):
            all_verifiers.add(result.get("model"))
    all_verifiers = list(all_verifiers)

    # For each pair of verifiers
    pairs_agreement = {}
    for i in range(len(all_verifiers)):
        for j in range(i+1, len(all_verifiers)):
            v1, v2 = all_verifiers[i], all_verifiers[j]

            shared_items = 0
            agreed_items = 0

            for item_id, item in merged_data.items():
                results_by_model = {}
                for result in item.get("verifier_results", []):
                    results_by_model[result.get("model")] = result.get("classification")

                # If both verifiers judged this item
                if v1 in results_by_model and v2 in results_by_model:
                    shared_items += 1
                    if results_by_model[v1] == results_by_model[v2]:
                        agreed_items += 1

            if shared_items > 0:
                agreement_rate = agreed_items / shared_items
                pairs_agreement[(v1, v2)] = {
                    "shared_items": shared_items,
                    "agreed_items": agreed_items,
                    "agreement_rate": agreement_rate
                }

    # Calculate overall agreement among all verifiers
    all_verifiers_agreement = {"total": 0, "agreed": 0}
    for item_id, item in merged_data.items():
        results_by_model = {}
        for result in item.get("verifier_results", []):
            results_by_model[result.get("model")] = result.get("classification")

        # If all verifiers judged this item
        if len(results_by_model) == len(all_verifiers) and len(all_verifiers) > 0:
            all_verifiers_agreement["total"] += 1

            # Check if all agreed
            classifications = set(results_by_model.values())
            if len(classifications) == 1:
                all_verifiers_agreement["agreed"] += 1

    if all_verifiers_agreement["total"] > 0:
        all_verifiers_agreement["agreement_rate"] = all_verifiers_agreement["agreed"] / all_verifiers_agreement["total"]
    else:
        all_verifiers_agreement["agreement_rate"] = 0

    return pairs_agreement, all_verifiers_agreement

def print_model_summary(merged_data, model_stats):
    """Print a summary of suitable/unsuitable papers and verifier agreement."""
    # First section: Suitability by unique elements
    print("\n" + "="*80)
    print("SUITABILITY SUMMARY BY UNIQUE ELEMENTS")
    print("="*80)

    # Get all unique generator and verifier models
    all_generator_models = set()
    all_verifier_models = set()
    for (gen_model, ver_model) in model_stats:
        all_generator_models.add(gen_model)
        all_verifier_models.add(ver_model)

    # Sort the models for consistent output
    all_generator_models = sorted(list(all_generator_models))
    all_verifier_models = sorted(list(all_verifier_models))

    # Print summary for each generator model
    for gen_model in all_generator_models:
        print(f"\nGenerator Model: {gen_model}")
        print("-" * 70)
        print(f"{'Verifier Model':<30} | {'Suitable':<10} | {'Unsuitable':<10} | {'Total':<10} | {'% Suitable':<10}")
        print("-" * 70)

        # Track unique items for this generator
        gen_suitable_ids = set()
        gen_unsuitable_ids = set()

        for ver_model in all_verifier_models:
            suitable_ids = model_stats.get((gen_model, ver_model), {}).get("Suitable", set())
            unsuitable_ids = model_stats.get((gen_model, ver_model), {}).get("Unsuitable", set())

            suitable = len(suitable_ids)
            unsuitable = len(unsuitable_ids)
            total = suitable + unsuitable

            if total > 0:
                percentage = (suitable / total) * 100
                print(f"{ver_model:<30} | {suitable:<10} | {unsuitable:<10} | {total:<10} | {percentage:.1f}%")
                gen_suitable_ids.update(suitable_ids)
                gen_unsuitable_ids.update(unsuitable_ids)

        # Generator totals based on unique IDs
        gen_suitable = len(gen_suitable_ids)
        gen_unsuitable = len(gen_unsuitable_ids)
        gen_total = gen_suitable + gen_unsuitable

        if gen_total > 0:
            gen_percentage = (gen_suitable / gen_total) * 100
            print("-" * 70)
            print(f"{'TOTAL UNIQUE ITEMS':<30} | {gen_suitable:<10} | {gen_unsuitable:<10} | {gen_total:<10} | {gen_percentage:.1f}%")

    # Second section: Agreement rates
    pairs_agreement, all_agreement = calculate_agreement_rates(merged_data)

    print("\n" + "="*80)
    print("AGREEMENT RATES BETWEEN VERIFIER MODELS")
    print("="*80)
    print(f"{'Verifier Pair':<40} | {'Shared Items':<15} | {'Agreed':<15} | {'Agreement Rate':<15}")
    print("-" * 90)

    for (v1, v2), stats in sorted(pairs_agreement.items()):
        pair_name = f"{v1} & {v2}"
        print(f"{pair_name:<40} | {stats['shared_items']:<15} | {stats['agreed_items']:<15} | {stats['agreement_rate']*100:.1f}%")

    print("\n" + "="*80)
    print("OVERALL AGREEMENT ACROSS ALL VERIFIERS")
    print("="*80)
    print(f"Total items evaluated by all verifiers: {all_agreement['total']}")
    print(f"Items with unanimous agreement: {all_agreement['agreed']}")
    if all_agreement['total'] > 0:
        print(f"Overall agreement rate: {all_agreement['agreement_rate']*100:.1f}%")
    else:
        print("Overall agreement rate: N/A (no items evaluated by all verifiers)")
    print("="*80)

    print("\n" + "="*80)
    print("FINAL SUITABILITY COUNTS (After Aggregation)")
    print("="*80)

    # Count items by final suitability
    final_suitable = sum(1 for item in merged_data.values() if item.get("suitability") == "Suitable")
    final_unsuitable = sum(1 for item in merged_data.values() if item.get("suitability") == "Unsuitable")
    final_total = len(merged_data)

    print(f"Final Suitable Items: {final_suitable}")
    print(f"Final Unsuitable Items: {final_unsuitable}")
    print(f"Total Unique Items: {final_total}")

    if final_total > 0:
        final_suitable_percentage = (final_suitable / final_total) * 100
        print(f"Overall Suitability Rate: {final_suitable_percentage:.1f}%")
    print("="*80)

def merge_verification_results(output_dir: str, merged_output_path: str, file_pattern: str) -> int:
    """
    Find all verifier output files and merge them into a single file.

    Args:
        output_dir: Directory where verifier output files are stored
        merged_output_path: Path to save the merged results
        file_pattern: Pattern to match verifier output files

    Returns:
        Number of items in the merged output
    """
    start_time = time.time()
    print("Starting verification results merge...")
    print(f"Looking for files matching pattern: {os.path.join(output_dir, file_pattern)}")

    # Find all verifier output files
    verifier_files = glob.glob(os.path.join(output_dir, file_pattern))

    # Skip the merged output file itself if it matches the pattern
    verifier_files = [f for f in verifier_files if os.path.abspath(f) != os.path.abspath(merged_output_path)]

    if not verifier_files:
        print("No verifier output files found. Nothing to merge.")
        return 0

    print(f"Found {len(verifier_files)} verifier output files to merge:")
    for vf in verifier_files:
        print(f"  - {os.path.basename(vf)}")

    # Load all verification data - use composite key of arxiv_id+content_id
    merged_data: Dict[str, Dict] = {}
    # Initialize counters
    total_lines_processed = 0
    total_unique_items = 0

    # Track statistics by generator and verifier model
    model_stats = defaultdict(lambda: defaultdict(set))

    for verifier_file in verifier_files:
        model_name = extract_model_name(os.path.basename(verifier_file))
        print(f"Processing: {verifier_file} (model: {model_name})")

        file_line_count = 0
        file_unique_items = set()

        try:
            with open(verifier_file, "r") as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        file_line_count += 1
                        item = json.loads(line.strip())
                        arxiv_id = item.get("arxiv_id")
                        conversations = item.get("conversations")
                        generator_model = item.get("model", "unknown")

                        if not arxiv_id:
                            print(f"  Warning: Line {line_num} missing arxiv_id, skipping")
                            continue

                        # Generate a unique ID based on conversations content
                        content_id = generate_content_id(conversations)
                        # Create a composite key using both arxiv_id and content_id
                        unique_key = f"{arxiv_id}_{content_id}"

                        # Track unique items in this file
                        file_unique_items.add(unique_key)

                        # Extract verification details
                        classification = item.get("suitability")
                        justification = item.get("verifier_justification")

                        # Skip if missing required data
                        if not classification:
                            print(f"  Warning: Entry for {arxiv_id} (content ID: {content_id}) missing classification, skipping")
                            continue

                        # Create a new entry if this unique key hasn't been seen yet
                        if unique_key not in merged_data:
                            # First time seeing this content, copy base item
                            base_item = {k: v for k, v in item.items()
                                        if k not in ["suitability", "verifier_justification", "verifier_model"]}
                            # Add the content ID for reference
                            base_item["content_id"] = content_id
                            merged_data[unique_key] = base_item
                            merged_data[unique_key]["verifier_results"] = []
                            total_unique_items += 1

                        # Create verifier result
                        verifier_result = {
                            "model": model_name,
                            "classification": classification,
                            "justification": justification,
                            "timestamp": item.get("timestamp", time.time())
                        }

                        # Add this verification result to the item
                        merged_data[unique_key]["verifier_results"].append(verifier_result)

                        # Update statistics - now storing sets of unique IDs
                        model_stats[(generator_model, model_name)][classification].add(unique_key)

                    except json.JSONDecodeError:
                        print(f"  Warning: Invalid JSON at line {line_num}")
                    except Exception as e:
                        print(f"  Error processing line {line_num}: {e}")

            total_lines_processed += file_line_count
            print(f"  Processed {file_line_count} lines, found {len(file_unique_items)} unique items in {model_name}")

        except Exception as e:
            print(f"Error processing file {verifier_file}: {e}")

    # Calculate suitability scores
    for unique_key, item in merged_data.items():
        verifier_results = item.get("verifier_results", [])
        suitable_count = sum(1 for vr in verifier_results if vr.get("classification") == "Suitable")
        total_verifiers = len(verifier_results)

        if total_verifiers > 0:
            suitability_score = suitable_count / total_verifiers
            item["suitability_score"] = suitability_score
            item["suitability"] = "Suitable" if suitability_score >= 0.5 else "Unsuitable"
        else:
            item["suitability_score"] = 0
            item["suitability"] = "Unsuitable"

    # Write merged data to output
    output_dir = os.path.dirname(merged_output_path)
    os.makedirs(output_dir, exist_ok=True)

    try:
        temp_file = f"{merged_output_path}.temp"
        with open(temp_file, "w") as f:
            for item in merged_data.values():
                f.write(json.dumps(item) + "\n")

        # Atomically replace the output file
        os.replace(temp_file, merged_output_path)

        end_time = time.time()
        print("\nMerge complete:")
        print(f"  Total lines processed: {total_lines_processed}")
        print(f"  Unique items: {len(merged_data)}")
        print(f"  Total verification results: {sum(len(item.get('verifier_results', [])) for item in merged_data.values())}")
        print(f"Merged file saved to: {merged_output_path}")
        print(f"Total merge time: {end_time - start_time:.2f} seconds")

        # Print the summary by generator and verifier model with agreement rates
        print_model_summary(merged_data, model_stats)

        return len(merged_data)
    except Exception as e:
        print(f"Error saving merged output: {e}")
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
        return 0

def main():
    """Parse command line arguments and run the merge."""
    parser = argparse.ArgumentParser(description='Merge verification results from multiple verifier models.')
    parser.add_argument('--output-dir', default=DEFAULT_OUTPUT_DIR,
                        help='Directory where verifier output files are stored')
    parser.add_argument('--merged-output', default=DEFAULT_MERGED_OUTPUT,
                        help='Path to save the merged results')
    parser.add_argument('--file-pattern', default=DEFAULT_FILE_PATTERN,
                        help='Pattern to match verifier output files')

    args = parser.parse_args()

    merge_verification_results(
        output_dir=args.output_dir,
        merged_output_path=args.merged_output,
        file_pattern=args.file_pattern
    )

if __name__ == "__main__":
    main()
