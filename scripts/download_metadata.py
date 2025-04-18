import arxiv
import time
import json
import argparse
from pathlib import Path

# arXiv API best practices: wait 3 seconds between requests.
RATE_LIMIT_DELAY = 3 # seconds

# Default number of papers per category
DEFAULT_NUM_PAPERS = 200

def download_arxiv_metadata(categories, num_papers_per_category, output_file):
    """
    Downloads metadata for a specified number of papers from given arXiv categories.

    Args:
        categories (list): A list of arXiv category strings (e.g., ['q-bio', 'econ.GN']).
        num_papers_per_category (int): The target number of papers per category.
        output_file (Path): The path to save the collected metadata (JSON Lines format).
    """
    client = arxiv.Client(
        page_size=100,       # Number of results per page fetched under the hood
        delay_seconds=RATE_LIMIT_DELAY, # Delay between consecutive page fetches Client makes
        num_retries=5        # Number of retries if a request fails
    )

    output_file.parent.mkdir(parents=True, exist_ok=True) # Ensure output dir exists

    print(f"Starting metadata download. Target: {num_papers_per_category} papers per category.")
    print(f"Output will be saved to: {output_file}")
    print(f"Using a delay of {RATE_LIMIT_DELAY} seconds between category searches.")

    with open(output_file, 'w', encoding='utf-8') as f: # Open file once to write line by line
        for category in categories:
            print(f"\n--- Fetching metadata for category: {category} ---")

            # Construct search query
            # Sort by last updated date to get a mix of recent activity
            # Using base categories like 'q-bio' or 'econ' is broad.
            # You could use subcategories like 'q-bio.PE' (Populations and Evolution)
            # or 'econ.TH' (Theoretical Economics) for more specificity.
            search = arxiv.Search(
                query = f"cat:{category}",
                max_results = num_papers_per_category,
                sort_by = arxiv.SortCriterion.LastUpdatedDate, # Or SubmittedDate or Relevance
                sort_order = arxiv.SortOrder.Descending
            )

            results_generator = client.results(search)

            count = 0
            papers_in_category = []
            try:
                for result in results_generator:
                    # Extract relevant metadata
                    paper_data = {
                        'arxiv_id': result.entry_id.split('/')[-1], # Get clean ID
                        'title': result.title,
                        'authors': [str(author) for author in result.authors],
                        'published_date': result.published.strftime('%Y-%m-%d'),
                        'updated_date': result.updated.strftime('%Y-%m-%d'),
                        'abstract': result.summary.replace('\n', ' '), # Clean abstract
                        'categories': result.categories,
                        'primary_category': result.primary_category,
                        'pdf_url': result.pdf_url,
                        'doi': result.doi
                    }
                    papers_in_category.append(paper_data)
                    f.write(json.dumps(paper_data) + '\n') # Write directly to file
                    count += 1
                    if count % 50 == 0:
                         print(f"  Fetched {count} papers for {category}...")

                print(f"  Successfully collected metadata for {count} papers in {category}.")
                # Note: arXiv might return slightly fewer than max_results if not available

            except Exception as e:
                print(f"  An error occurred while fetching results for {category}: {e}")
                # Continue to the next category

            # Explicitly wait before starting the next category search,
            # even though the client has internal delays for paging.
            # This respects the spirit of not hitting the *search* endpoint too rapidly.
            if category != categories[-1]: # Don't wait after the last category
                print(f"  Waiting {RATE_LIMIT_DELAY} seconds before next category...")
                time.sleep(RATE_LIMIT_DELAY)

    print("\n--- Download complete ---")
    print(f"Metadata saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Download metadata from arXiv for specified categories.")
    parser.add_argument(
        "--categories",
        nargs='+', # Allows multiple categories
        default=['q-bio', 'econ.GN'], # Default categories (econ.GN = General Economics)
        help="List of arXiv categories (e.g., q-bio econ.GN cs.AI)."
    )
    parser.add_argument(
        "--num_papers",
        type=int,
        default=DEFAULT_NUM_PAPERS,
        help=f"Number of papers to attempt to download per category (default: {DEFAULT_NUM_PAPERS})."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/arxiv_metadata.jsonl"), # Save in data directory
        help="Output file path for the metadata (JSON Lines format)."
    )
    args = parser.parse_args()

    download_arxiv_metadata(args.categories, args.num_papers, args.output)

if __name__ == "__main__":
    main()
