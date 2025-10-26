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

def setup_logging(config):
    log_level = getattr(logging, config['logging']['level'])
    log_file = config['logging']['file']

    # Replace timestamp placeholder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_file.replace("{timestamp}", timestamp)

    # Create logs directory
    Path(log_file).parent.mkdir(exist_ok=True)

    # Configure logging
    handlers = [logging.FileHandler(log_file)]
    if config['logging']['console']:
        handlers.append(logging.StreamHandler())

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

def load_input_papers(input_path: str):
    """Load papers from input JSON file"""
    with open(input_path, 'r', encoding='utf-8') as f:
        papers = json.load(f)
    return papers

def main():
    # Load config
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    setup_logging(config)
    logger = logging.getLogger(__name__)

    logger.info("="*60)
    logger.info("Starting OpenReview Paper Processing")
    logger.info("="*60)

    # Load input papers
    input_json = config['storage']['input_json']
    logger.info(f"Loading papers from: {input_json}")
    papers = load_input_papers(input_json)
    logger.info(f"Loaded {len(papers)} papers")

    # Initialize processor
    processor = PaperProcessor(config)

    # Process papers
    results = {
        "completed": [],
        "failed_download": [],
        "failed_conversion": [],
        "skipped": []
    }

    logger.info("Starting paper processing...")
    for paper in tqdm(papers, desc="Processing papers"):
        result = processor.process_paper(paper)

        status = result['status']
        if status in results:
            results[status].append(result['paper_id'])

    # Print summary
    logger.info("="*60)
    logger.info("Processing Summary:")
    logger.info(f"  Total papers: {len(papers)}")
    logger.info(f"  Completed: {len(results['completed'])}")
    logger.info(f"  Skipped (already processed): {len(results['skipped'])}")
    logger.info(f"  Failed (download): {len(results['failed_download'])}")
    logger.info(f"  Failed (conversion): {len(results['failed_conversion'])}")
    logger.info("="*60)

    # Save processing summary
    summary_path = Path(config['storage']['base_dir']) / "index" / "processing_summary.json"
    summary_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total_papers": len(papers),
        "results": results,
        "config": config
    }

    with open(summary_path, 'w') as f:
        json.dump(summary_data, f, indent=2)

    logger.info(f"Processing summary saved to: {summary_path}")

    # Show final stats
    stats = processor.get_processing_stats()
    logger.info("Final Statistics:")
    logger.info(f"  Index stats: {stats['index_stats']}")
    logger.info(f"  Log entries: {stats['total_log_entries']}")

if __name__ == "__main__":
    main()
