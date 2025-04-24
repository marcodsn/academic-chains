#!/usr/bin/env python3
import os
import json
import queue
import tempfile
import threading
import subprocess
import multiprocessing
from multiprocessing import Process, Queue
import time
import argparse
from pathlib import Path
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling_core.types.doc import ImageRefMode, PictureItem
import shutil
import io
import uuid
import boto3
from dotenv import load_dotenv

load_dotenv()

multiprocessing.set_start_method('spawn', force=True)  # CUDA requires spawn

IMAGE_RESOLUTION_SCALE = 2.0


def upload_to_r2(image_data, filename, content_type='image/jpeg'):
    """Upload image to Cloudflare R2 and return the public URL"""
    # Initialize R2 client (ideally once per batch outside this function)
    s3_client = boto3.client(
        's3',
        endpoint_url = os.getenv("R2_ENDPOINT"),
        aws_access_key_id = os.getenv("R2_KEY_ID"),
        aws_secret_access_key = os.getenv("R2_KEY_SECRET"),
        region_name = os.getenv("R2_REGION", "auto")
    )

    # Upload the image
    s3_client.put_object(
        Bucket = 'arxiv-markdown-images',
        Key = f"{filename}",
        Body = image_data,
        ContentType = content_type
    )

    # Return the public URL
    return f"https://ac.marcodsn.me/arxiv-markdown-images/{filename}"


def batch_convert_worker(paper_batch_info, result_queue, worker_id):
    """
    Worker function to be run in a separate process.
    Initializes ONE DocumentConverter and processes a BATCH of papers.
    """
    os.environ['CUDA_VISIBLE_DEVICES'] = '0'

    results_list = []
    converter = None # Initialize later inside try block

    print(f"[Worker {worker_id}] Started. Processing batch of {len(paper_batch_info)} papers.")
    start_time_batch = time.time()

    try:
        # Initialize converter ONCE for the batch
        print(f"[Worker {worker_id}] Initializing DocumentConverter...")
        pipeline_options = PdfPipelineOptions()
        pipeline_options.images_scale = IMAGE_RESOLUTION_SCALE
        pipeline_options.generate_page_images = True
        pipeline_options.generate_picture_images = True
        pipeline_options.do_code_enrichment = True
        pipeline_options.do_formula_enrichment = True
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        print(f"[Worker {worker_id}] DocumentConverter initialized.")

        # Loop through papers in the batch
        for i, paper_info in enumerate(paper_batch_info):
            arxiv_id = paper_info.get('arxiv_id', 'unknown')
            local_path = paper_info.get('local_path')
            temp_dir = paper_info.get('temp_dir') # Get temp dir for cleanup
            print(f"[Worker {worker_id}] Processing paper {i+1}/{len(paper_batch_info)}: {arxiv_id}")
            start_time_paper = time.time()
            paper_result = None

            if not local_path or not os.path.exists(local_path):
                 print(f"[Worker {worker_id}] Error: PDF path missing or not found for {arxiv_id} at {local_path}")
                 paper_result = {"arxiv_id": arxiv_id, "error": "PDF path missing or invalid."}
                 results_list.append(paper_result)
                 # Still attempt cleanup of temp_dir if it exists
                 if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
                 continue # Skip to next paper

            try:
                # Convert using docling
                result = converter.convert(local_path)

                # Extract and upload images to Cloudflare R2
                image_urls = []

                # Process figures
                for element, _level in result.document.iterate_items():
                    if isinstance(element, PictureItem) and hasattr(element, 'get_image'):
                        # Generate unique ID for the figure
                        figure_id = str(uuid.uuid4())
                        image_filename = f"{arxiv_id}-figure-{figure_id}.jpg"

                        # Get image, convert to JPEG and upload
                        pil_img = element.get_image(result.document)
                        jpeg_data = io.BytesIO()
                        pil_img.convert('RGB').save(jpeg_data, format='JPEG', quality=95)
                        jpeg_data.seek(0)

                        # Upload and store URL
                        r2_url = upload_to_r2(jpeg_data, image_filename, content_type='image/jpeg')
                        print(f"Uploaded image {image_filename} to R2, URL: {r2_url}")
                        image_urls.append(r2_url)

                markdown = result.document.export_to_markdown(image_mode=ImageRefMode.PLACEHOLDER, image_placeholder="<!-- image -->")
                # Replace <!-- image --> with the actual image URLs
                for i, url in enumerate(image_urls):
                    markdown = markdown.replace(f"<!-- image -->", f"![image]({url})", 1)

                # Create result object for this paper
                paper_result = {
                    "arxiv_id": arxiv_id,
                    "markdown": markdown,
                }
                results_list.append(paper_result)
                print(f"[Worker {worker_id}] Successfully converted {arxiv_id} in {time.time() - start_time_paper:.2f}s")

            except Exception as e:
                print(f"[Worker {worker_id}] Error converting {arxiv_id}: {e}")
                # Add error info for this specific paper
                results_list.append({"arxiv_id": arxiv_id, "error": str(e)})
            finally:
                # Clean up temporary directory for THIS paper
                if temp_dir and os.path.exists(temp_dir):
                    try:
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        # print(f"[Worker {worker_id}] Cleaned up temp dir: {temp_dir}")
                    except Exception as cleanup_e:
                        print(f"[Worker {worker_id}] Error cleaning up temp dir {temp_dir} for {arxiv_id}: {cleanup_e}")

        # Put the list of all results (successes and errors) for the batch onto the queue
        result_queue.put(results_list)
        total_batch_time = time.time() - start_time_batch
        print(f"[Worker {worker_id}] Finished batch of {len(paper_batch_info)} in {total_batch_time:.2f}s.")

    except Exception as batch_e:
        # Handle errors during converter initialization or other batch-level issues
        print(f"[Worker {worker_id}] CRITICAL BATCH ERROR: {batch_e}")
        # Try to send back whatever results were gathered, plus an error marker
        results_list.append({"batch_error": str(batch_e)})
        result_queue.put(results_list)
        # Clean up any remaining temp dirs for this batch if possible (best effort)
        for paper_info in paper_batch_info:
            if paper_info.get("temp_dir") and os.path.exists(paper_info.get("temp_dir")):
                 shutil.rmtree(paper_info.get("temp_dir"), ignore_errors=True)

    finally:
        # Optional: Explicitly release converter resources if needed
        # del converter
        pass


class ArxivProcessor:
    def __init__(self, month, year, output_dir, batch_size=8, prefetch_factor=3, timeout=300):
        self.month = month.zfill(2)
        self.year = year
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.batch_size = batch_size
        self.prefetch_factor = prefetch_factor
        # IMPORTANT: This timeout now applies to the WHOLE BATCH
        self.batch_timeout = timeout * batch_size # Start with a scaled timeout, adjust as needed
        print(f"Setting BATCH timeout to {self.batch_timeout} seconds ({timeout}s per paper * {batch_size} papers)")

        self.temp_base_dir = tempfile.mkdtemp(prefix="arxiv_processing_")
        print(f"Using temporary directory: {self.temp_base_dir}")
        self.dataset_path = self.output_dir / f"arxiv_{year}{self.month}.jsonl"
        self.checkpoint_path = self.output_dir / f"arxiv_{year}{self.month}.checkpoint"
        self.paper_queue = queue.Queue(maxsize=prefetch_factor * batch_size)
        self.processed_ids = set()
        self.load_checkpoint()
        self.worker_process_counter = 0 # To give workers IDs for logging

    def __del__(self):
        try:
            if hasattr(self, 'temp_base_dir') and os.path.exists(self.temp_base_dir):
                shutil.rmtree(self.temp_base_dir, ignore_errors=True)
                print(f"Cleaned up base temporary directory: {self.temp_base_dir}")
        except Exception as e:
             print(f"Error cleaning up base temp dir: {e}")

    def load_checkpoint(self):
        if self.checkpoint_path.exists():
            with open(self.checkpoint_path, 'r') as f:
                self.processed_ids = set(line.strip() for line in f)
            print(f"Resuming from checkpoint with {len(self.processed_ids)} processed papers")

    def update_checkpoint(self, paper_id):
        with open(self.checkpoint_path, 'a') as f:
            f.write(f"{paper_id}\n")

    def list_papers(self):
        cmd = f"gsutil ls gs://arxiv-dataset/arxiv/arxiv/pdf/{self.year}{self.month}/*.pdf"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error listing papers: {result.stderr}")
            return []

        paper_urls = result.stdout.strip().split('\n')
        paper_urls = [url for url in paper_urls if url.strip()]  # Filter out empty strings

        # Group papers by base ID (without version suffix)
        paper_versions = {}
        for url in paper_urls:
            if not url:
                continue

            try:
                filename = url.split('/')[-1]
                paper_id = filename.replace('.pdf', '')

                # Extract base ID and version
                if 'v' in paper_id:
                    base_id, version_str = paper_id.rsplit('v', 1)
                    try:
                        version_num = int(version_str)
                    except ValueError:
                        print(f"Warning: Invalid version in {paper_id}, treating as v1")
                        version_num = 1
                else:
                    base_id = paper_id
                    version_num = 1

                # Keep track of highest version for each base ID
                if base_id not in paper_versions or version_num > paper_versions[base_id]['version']:
                    paper_versions[base_id] = {
                        'version': version_num,
                        'full_id': paper_id,
                        'url': url
                    }
            except Exception as e:
                print(f"Warning: Could not parse paper ID from URL: {url} - {e}")

        # Select only the latest version of each paper that hasn't been processed
        new_papers = []
        for base_id, paper_info in paper_versions.items():
            full_id = paper_info['full_id']
            if full_id not in self.processed_ids:
                new_papers.append({"arxiv_id": full_id, "url": paper_info['url']})

        print(f"Found {len(paper_urls)} total PDF files")
        print(f"Identified {len(paper_versions)} unique papers (after grouping versions)")
        print(f"Found {len(new_papers)} new papers to process (latest versions only)")

        return new_papers

    def download_paper(self, paper):
        paper_dir = None
        try:
            paper_dir = tempfile.mkdtemp(prefix=f"{paper['arxiv_id']}_", dir=self.temp_base_dir)
            pdf_path = Path(paper_dir) / f"{paper['arxiv_id']}.pdf"
            # print(f"Downloading {paper['arxiv_id']} to {pdf_path}") # Less verbose download
            cmd = f"gsutil cp {paper['url']} {pdf_path}"
            result = subprocess.run(cmd, shell=True, check=False, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                 raise Exception(f"gsutil failed: {result.stderr}")
            # print(f"Successfully downloaded {paper['arxiv_id']}") # Less verbose download
            return {**paper, "local_path": str(pdf_path), "temp_dir": paper_dir}
        except subprocess.TimeoutExpired:
            print(f"Timeout downloading {paper['arxiv_id']}")
            if paper_dir and os.path.exists(paper_dir): shutil.rmtree(paper_dir, ignore_errors=True)
            return None
        except Exception as e:
            print(f"Error downloading {paper['arxiv_id']}: {e}")
            if paper_dir and os.path.exists(paper_dir): shutil.rmtree(paper_dir, ignore_errors=True)
            return None

    def downloader_thread(self, papers_metadata):
        download_count = 0
        total_papers = len(papers_metadata)
        queue_max_size = self.paper_queue.maxsize
        print(f"[Downloader] Started. Target: {total_papers} papers. Prefetch queue max size: {queue_max_size}")
        try:
            for paper in papers_metadata:
                try:
                    paper_data = self.download_paper(paper)
                    if paper_data is not None:
                        if self.paper_queue.full():
                            current_size = self.paper_queue.qsize() # Get current size (should be maxsize)
                            print(f"[Downloader] Prefetch queue is FULL (Size: {current_size}/{queue_max_size}). Waiting for processor to consume items...")

                        self.paper_queue.put(paper_data)
                        download_count += 1
                    else:
                         print(f"Marking failed download {paper.get('arxiv_id', 'unknown')} as processed.")
                         self.update_checkpoint(paper.get('arxiv_id', 'unknown'))
                except Exception as e:
                    print(f"Error in download loop for {paper.get('arxiv_id', 'unknown')}: {e}")
                    self.update_checkpoint(paper.get('arxiv_id', 'unknown'))
        finally:
            print(f"Downloader thread finished. Downloaded {download_count} papers.")
            self.paper_queue.put(None)

    def convert_batch_with_process_timeout(self, paper_batch_info, **kwargs):
        """
        Runs the BATCH conversion in a single separate process with timeout handling.
        """
        # Use the class's batch timeout if not overridden
        timeout = kwargs.get('timeout', self.batch_timeout)
        result_queue = Queue()
        self.worker_process_counter += 1
        worker_id = self.worker_process_counter

        # Target is the batch worker function
        proc = Process(
            target=batch_convert_worker,
            args=(paper_batch_info, result_queue, worker_id) # Pass the list of paper info
        )

        start_time = time.time()
        proc.start()
        print(f"Started BATCH worker process {proc.pid} (ID: {worker_id}) for {len(paper_batch_info)} papers.")

        batch_results = None
        try:
            # Wait for the process to finish or the BATCH timeout
            batch_results = result_queue.get(timeout=timeout)
            proc.join() # Ensure process is joined after getting result
            print(f"Batch worker process {proc.pid} (ID: {worker_id}) finished in {time.time() - start_time:.2f}s")
            return batch_results # Return the list of results from the queue

        except queue.Empty:
            print(f"BATCH CONVERSION TIMEOUT after {timeout}s for worker {proc.pid} (ID: {worker_id})")
            if proc.is_alive():
                print(f"Terminating BATCH process {proc.pid}")
                proc.terminate()
                proc.join(5)
                if proc.is_alive():
                    print(f"Force killing BATCH process {proc.pid} (SIGKILL)")
                    try: os.kill(proc.pid, 9); proc.join(1)
                    except: pass

            # Need to mark all papers in this timed-out batch as processed in checkpoint
            # and clean up their temp dirs from parent if possible
            print(f"Marking {len(paper_batch_info)} papers from timed-out batch as processed.")
            error_result_list = []
            for paper_info in paper_batch_info:
                arxiv_id = paper_info.get("arxiv_id", "unknown_in_timeout")
                error_result_list.append({"arxiv_id": arxiv_id, "error": f"Batch timeout after {timeout}s"})
                self.update_checkpoint(arxiv_id) # Mark as processed to avoid retrying
                # Parent attempts cleanup if worker was killed
                if "temp_dir" in paper_info and os.path.exists(paper_info["temp_dir"]):
                     # print(f"Parent cleaning up temp dir after timeout: {paper_info['temp_dir']}")
                     shutil.rmtree(paper_info["temp_dir"], ignore_errors=True)
            return error_result_list # Return list indicating timeout for all

        except Exception as e:
            print(f"Error managing BATCH process {proc.pid} (ID: {worker_id}): {e}")
            # Similar cleanup and marking as timeout case
            if proc.is_alive():
                 proc.terminate(); proc.join(5)
                 if proc.is_alive():
                     try: os.kill(proc.pid, 9); proc.join(1)
                     except: pass

            error_result_list = []
            for paper_info in paper_batch_info:
                 arxiv_id = paper_info.get("arxiv_id", "unknown_in_error")
                 error_result_list.append({"arxiv_id": arxiv_id, "error": f"Batch process management error: {str(e)}"})
                 self.update_checkpoint(arxiv_id) # Mark as processed
                 if "temp_dir" in paper_info and os.path.exists(paper_info["temp_dir"]):
                     shutil.rmtree(paper_info["temp_dir"], ignore_errors=True)
            return error_result_list


    def run(self):
        """Main execution flow using batch workers"""
        if not self.dataset_path.exists():
            with open(self.dataset_path, "w") as f: pass

        papers_metadata = self.list_papers()
        if not papers_metadata:
            print("No new papers to process based on checkpoint.")
            self.__del__()
            return

        downloader = threading.Thread(target=self.downloader_thread, args=(papers_metadata,))
        downloader.daemon = True
        downloader.start()

        total_to_process_estimate = len(papers_metadata)
        papers_processed_successfully = 0
        papers_attempted = len(self.processed_ids)

        while True:
            current_batch_info = []
            batch_full = False
            try:
                # Gather a full batch
                while len(current_batch_info) < self.batch_size:
                     paper_data = self.paper_queue.get(timeout=600) # Wait for papers
                     if paper_data is None: # Sentinel found
                         break # Stop filling batch
                     current_batch_info.append(paper_data)
                else: # Executed if the while loop finished without break (i.e. batch is full)
                    batch_full = True

            except queue.Empty:
                 print("Warning: Timed out waiting for paper from download queue.")
                 if not downloader.is_alive() and self.paper_queue.empty():
                     print("Downloader finished and queue is empty.")
                     break # Exit loop gracefully if downloads are done
                 # If queue timed out but downloader might still be running,
                 # process whatever we have in current_batch_info (if any) below

            # --- Process the gathered batch ---
            if current_batch_info:
                 print(f"\nProcessing batch of {len(current_batch_info)} papers...")
                 start_time = time.time()

                 # Process the whole batch in one worker process
                 # Pass the batch-specific timeout
                 batch_results = self.convert_batch_with_process_timeout(
                     current_batch_info,
                     timeout=self.batch_timeout
                 )

                 processed_in_batch_count = 0
                 # Process results for each paper in the batch
                 if isinstance(batch_results, list):
                     for result in batch_results:
                         arxiv_id = result.get("arxiv_id", "unknown_result")
                         if "error" in result:
                             print(f"Failed to process {arxiv_id}: {result['error']}")
                             # Checkpoint is updated EVEN IF FAILED in this model
                             # (either by worker finally block or parent timeout handler)
                         elif "markdown" in result:
                             # Append successful conversion to JSONL
                             with open(self.dataset_path, "a") as output_file:
                                 output_file.write(json.dumps(result) + "\n")
                             # print(f"Successfully processed {arxiv_id}") # Less verbose
                             processed_in_batch_count += 1
                         elif "batch_error" in result:
                             # This indicates a fatal error within the batch worker itself
                             print(f"Batch worker failed critically: {result['batch_error']}")
                             # Papers might have already been checkpointed in worker/timeout handler

                         # Checkpoint update: In this batch model, it's often better to
                         # update checkpoint *after* the batch attempt is complete (here)
                         # or within the timeout/error handler of the parent process.
                         # The worker could also update it, but parent handling is safer
                         # if the worker crashes. We added updates in the parent's timeout/error
                         # handlers and will add it here for papers that didn't error out
                         # during the batch process itself (but might have had conversion errors)
                         if "batch_error" not in result: # Avoid double checkpointing if batch failed entirely
                             self.update_checkpoint(arxiv_id)

                 else: # Unexpected result type
                      print(f"Error: Unexpected result type from batch worker: {type(batch_results)}")
                      # Mark all papers in the batch as processed to avoid retries
                      for paper_info in current_batch_info:
                          self.update_checkpoint(paper_info.get("arxiv_id", "unknown_batch_error"))


                 papers_processed_successfully += processed_in_batch_count
                 papers_attempted += len(current_batch_info) # Increment attempted count
                 print(f"Batch finished in {time.time() - start_time:.2f}s. Attempted: {papers_attempted}. Successful this run: {papers_processed_successfully}.")

            # Check if the sentinel was the reason we stopped filling the batch or if queue timed out empty
            if not batch_full and (paper_data is None or (not current_batch_info and not downloader.is_alive() and self.paper_queue.empty())):
                 break # Exit main loop if downloads are done

        print("Waiting for downloader thread to complete...")
        downloader.join(timeout=10)
        if downloader.is_alive(): print("Downloader thread still active.")

        print(f"\n--- Processing Summary ---")
        print(f"Month/Year: {self.year}-{self.month}")
        print(f"Initial estimate of papers to process: {total_to_process_estimate}")
        print(f"Total papers attempted (including previous runs): {papers_attempted}")
        print(f"Papers successfully converted in this run: {papers_processed_successfully}")
        print(f"Results saved to: {self.dataset_path}")
        print(f"Checkpoint file: {self.checkpoint_path}")
        self.__del__()


def main():
    parser = argparse.ArgumentParser(description="arXiv PDF to Markdown Converter (Batch Worker)")
    parser.add_argument("--month", required=True, help="Month (01-12)")
    parser.add_argument("--year", required=True, help="Year (e.g., 21 for 2021)")
    parser.add_argument("--output", default="./data/arxiv_md", help="Output directory")
    parser.add_argument("--batch-size", type=int, default=4, help="Number of papers processed per worker process")
    parser.add_argument("--prefetch", type=int, default=3, help="Download queue size factor (prefetch * batch_size)")
    # --- Adjusted Timeout Help Text ---
    parser.add_argument("--timeout-per-paper", type=int, default=240,
                        help="Estimated timeout PER PAPER in seconds. Total batch timeout will be this * batch_size.")

    args = parser.parse_args()

    processor = ArxivProcessor(
        month=args.month,
        year=args.year,
        output_dir=args.output,
        batch_size=args.batch_size,
        prefetch_factor=args.prefetch,
        # Pass the per-paper timeout; the constructor calculates the batch timeout
        timeout=args.timeout_per_paper
    )

    processor.run()

if __name__ == "__main__":
    main()
