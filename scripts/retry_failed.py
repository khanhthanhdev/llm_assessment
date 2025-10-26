#!/usr/bin/env python3
import json
import yaml
import logging
from pathlib import Path
import sys
from tqdm import tqdm
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processor import PaperProcessor
from src.storage_manager import StorageManager

def setup_logging(config):
    log_level = getattr(logging, config['logging']['level'])
    log_file = config['logging']['file']

    # Replace timestamp placeholder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_file.replace("{timestamp}", timestamp)

    # Create logs directory
    Path(log_file).parent.mkdir(exist_ok=True)

    handlers = [logging.FileHandler(log_file)]
    if config['logging']['console']:
        handlers.append(logging.StreamHandler())

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

def load_failed_papers(input_path: str, storage: StorageManager):
    """Load papers that failed processing"""
    with open(input_path, 'r', encoding='utf-8') as f:
        all_papers = json.load(f)

    failed_papers = []
    index = storage.load_index()

    for paper in all_papers:
        paper_id = paper['paper_id']
        paper_status = index['papers'].get(paper_id, {}).get('status', 'unknown')

        if paper_status in ['failed_download', 'failed_conversion', 'pending']:
            failed_papers.append(paper)

    return failed_papers

def main():
    # Load config
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    setup_logging(config)
    logger = logging.getLogger(__name__)

    logger.info("="*60)
    logger.info("Retrying Failed OpenReview Paper Processing")
    logger.info("="*60)

    # Initialize storage and processor
    storage = StorageManager(config['storage']['base_dir'])
    processor = PaperProcessor(config)

    # Load failed papers
    input_json = config['storage']['input_json']
    logger.info(f"Loading papers from: {input_json}")
    failed_papers = load_failed_papers(input_json, storage)
    logger.info(f"Found {len(failed_papers)} papers to retry")

    if not failed_papers:
        logger.info("No failed papers found. Nothing to retry.")
        return

    # Process failed papers
    results = {
        "completed": [],
        "failed_download": [],
        "failed_conversion": [],
        "skipped": []
    }

    logger.info("Retrying failed papers...")
    for paper in tqdm(failed_papers, desc="Retrying papers"):
        result = processor.process_paper(paper)

        status = result['status']
        if status in results:
            results[status].append(result['paper_id'])

    # Print summary
    logger.info("="*60)
    logger.info("Retry Summary:")
    logger.info(f"  Total retried: {len(failed_papers)}")
    logger.info(f"  Now completed: {len(results['completed'])}")
    logger.info(f"  Still failed (download): {len(results['failed_download'])}")
    logger.info(f"  Still failed (conversion): {len(results['failed_conversion'])}")
    logger.info("="*60)

if __name__ == "__main__":
    main()
