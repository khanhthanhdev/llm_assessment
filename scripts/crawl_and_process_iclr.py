#!/usr/bin/env python3
"""
Master script to crawl ICLR papers and process them (download PDFs + convert to markdown)
"""

import sys
import os
import json
from pathlib import Path
import time
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crawler.crawl import crawl_iclr_papers_and_reviews, save_data
from src.processor import PaperProcessor
import yaml

def load_config():
    """Load configuration from config.yaml"""
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def crawl_iclr_papers(year=2024, accepted_only=False, limit=None):
    """
    Crawl ICLR papers using the existing crawler
    """
    print(f"{'='*60}")
    print(f"Crawling ICLR {year} papers...")
    print(f"Mode: {'ACCEPTED ONLY' if accepted_only else 'ALL PAPERS'}")
    if limit:
        print(f"Limit: {limit} papers")
    print(f"{'='*60}")

    # Crawl papers
    papers = crawl_iclr_papers_and_reviews(
        year=year,
        accepted_only=accepted_only,
        limit=limit
    )

    if not papers:
        print("❌ No papers crawled. Check your OpenReview credentials and network connection.")
        return None

    print(f"✓ Successfully crawled {len(papers)} papers")

    # Save to JSON file that processing pipeline expects
    # Convert Paper objects to dictionaries
    papers_dict = []
    for paper in papers:
        if hasattr(paper, 'model_dump'):
            paper_dict = paper.model_dump()
        else:
            paper_dict = paper

        # Ensure required fields for processing pipeline
        paper_dict.setdefault('paper_id', paper_dict.get('id', f'unknown_{len(papers_dict)}'))
        paper_dict.setdefault('title', paper_dict.get('title', 'Unknown Title'))
        paper_dict.setdefault('pdf_url', paper_dict.get('pdf_url', ''))
        paper_dict.setdefault('authors', paper_dict.get('authors', []))
        paper_dict.setdefault('abstract', paper_dict.get('abstract', ''))

        papers_dict.append(paper_dict)

    # Save to the expected input format for processing
    output_file = f"iclr_{year}_papers_reviews{'_accepted' if accepted_only else ''}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(papers_dict, f, indent=2, ensure_ascii=False)

    print(f"✓ Saved crawled data to: {output_file}")
    return output_file

def process_papers(input_json, config, limit=None):
    """
    Process papers through the pipeline (download PDFs + convert to markdown)
    """
    print(f"\n{'='*60}")
    print("Starting paper processing pipeline...")
    print(f"Input file: {input_json}")
    print(f"{'='*60}")

    # Load papers from JSON
    try:
        with open(input_json, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Handle different JSON formats
        if isinstance(data, list):
            # Direct array of papers
            papers = data
        elif isinstance(data, dict) and 'papers' in data:
            # Wrapped format with metadata
            papers = data['papers']
        else:
            print(f"❌ Unexpected JSON format in {input_json}")
            return False

        print(f"✓ Loaded {len(papers)} papers from {input_json}")
    except Exception as e:
        print(f"❌ Failed to load papers from {input_json}: {e}")
        return False

    # Apply limit if specified
    if limit and len(papers) > limit:
        papers = papers[:limit]
        print(f"✓ Limited to first {len(papers)} papers")

    # Initialize processor
    processor = PaperProcessor(config)

    # Process papers
    results = {
        "completed": [],
        "failed_download": [],
        "failed_conversion": [],
        "skipped": []
    }

    start_time = time.time()

    print("\nProcessing papers...")
    for i, paper in enumerate(papers, 1):
        paper_id = paper.get('paper_id', f'paper_{i}')
        title = paper.get('title', 'Unknown')[:50]

        print(f"[{i}/{len(papers)}] Processing: {title}...")

        result = processor.process_paper(paper)

        status = result['status']
        if status in results:
            results[status].append(result['paper_id'])

        # Show brief status
        if status == 'completed':
            print("  ✓ Completed")
        elif status == 'skipped':
            print("  ⏭️  Skipped (already processed)")
        elif status == 'failed_download':
            print("  ❌ Failed (PDF download)")
        elif status == 'failed_conversion':
            print("  ❌ Failed (markdown conversion)")
        else:
            print(f"  ❓ {status}")

    # Save processing summary
    summary_path = Path(config['storage']['base_dir']) / "index" / "crawl_and_process_summary.json"
    summary_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "input_file": input_json,
        "total_papers": len(papers),
        "results": results,
        "processing_time_seconds": time.time() - start_time,
        "config": config
    }

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, 'w') as f:
        json.dump(summary_data, f, indent=2)

    # Print final summary
    print(f"\n{'='*60}")
    print("Processing Complete!")
    print(f"{'='*60}")
    print(f"Total papers processed: {len(papers)}")
    print(f"Completed: {len(results['completed'])}")
    print(f"Skipped: {len(results['skipped'])}")
    print(f"Failed downloads: {len(results['failed_download'])}")
    print(f"Failed conversions: {len(results['failed_conversion'])}")
    print(f"Total time: {time.time() - start_time:.1f} seconds")
    print(f"Summary saved to: {summary_path}")

    success_count = len(results['completed'])
    return success_count > 0

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Crawl ICLR papers and process them")
    parser.add_argument('--year', type=int, default=2024, help='ICLR year to crawl (default: 2024)')
    parser.add_argument('--accepted-only', action='store_true', help='Only crawl accepted papers')
    parser.add_argument('--limit', type=int, help='Limit number of papers to crawl')
    parser.add_argument('--skip-crawl', action='store_true', help='Skip crawling, use existing JSON file')
    parser.add_argument('--input-file', help='Use specific input JSON file instead of crawling')

    args = parser.parse_args()

    # Load configuration
    config = load_config()

    print("🚀 ICLR Paper Crawler & Processor")
    print(f"Year: {args.year}")
    print(f"Mode: {'ACCEPTED ONLY' if args.accepted_only else 'ALL PAPERS'}")
    if args.limit:
        print(f"Limit: {args.limit} papers")
    print()

    # Determine input file
    if args.input_file:
        input_json = args.input_file
        if not Path(input_json).exists():
            print(f"❌ Input file not found: {input_json}")
            return 1
        print(f"Using existing input file: {input_json}")
    elif args.skip_crawl:
        # Try to find existing file
        pattern = f"iclr_{args.year}_papers_reviews{'_accepted' if args.accepted_only else ''}.json"
        if Path(pattern).exists():
            input_json = pattern
            print(f"Using existing file: {input_json}")
        else:
            print(f"❌ No existing file found: {pattern}")
            print("Run without --skip-crawl to crawl papers first")
            return 1
    else:
        # Crawl papers
        input_json = crawl_iclr_papers(
            year=args.year,
            accepted_only=args.accepted_only,
            limit=args.limit
        )

        if not input_json:
            return 1

    # Process papers
    success = process_papers(input_json, config, args.limit)

    if success:
        print("\n🎉 All done! Check the data/papers/ directory for processed papers.")
        return 0
    else:
        print("\n❌ Processing failed or no papers were processed successfully.")
        return 1

if __name__ == "__main__":
    exit(main())
