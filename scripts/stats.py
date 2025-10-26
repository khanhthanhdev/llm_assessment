#!/usr/bin/env python3
import json
import yaml
from pathlib import Path
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage_manager import StorageManager

def load_config():
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def format_bytes(bytes_size):
    """Format bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} {unit}"

def main():
    config = load_config()
    storage = StorageManager(config['storage']['base_dir'])

    print("="*60)
    print("OpenReview Paper Processing Statistics")
    print("="*60)

    # Load index and log
    index = storage.load_index()
    log_entries = storage.load_processing_log()

    stats = index['stats']

    print("\nOverall Statistics:")
    print(f"  Total papers: {stats['total']}")
    completion_rate = stats['completed']/stats['total']*100 if stats['total'] > 0 else 0
    print(f"  Completed: {stats['completed']} ({completion_rate:.1f}%)")
    print(f"  PDFs downloaded: {stats['pdf_downloaded']}")
    print(f"  Markdown generated: {stats['markdown_generated']}")
    print(f"  Failed downloads: {stats['failed_download']}")
    print(f"  Failed conversions: {stats['failed_conversion']}")
    print(f"  Pending: {stats['pending']}")

    if index['last_updated']:
        print(f"  Last updated: {index['last_updated']}")

    print("\nProcessing Log:")
    print(f"  Total log entries: {len(log_entries)}")

    # Analyze log entries
    stages = {}
    for entry in log_entries:
        stage = entry['stage']
        status = entry['status']
        duration = entry.get('duration_seconds', 0)

        if stage not in stages:
            stages[stage] = {'count': 0, 'success': 0, 'failed': 0, 'total_duration': 0}

        stages[stage]['count'] += 1
        stages[stage]['total_duration'] += duration

        if status == 'success':
            stages[stage]['success'] += 1
        elif status in ['failed', 'error']:
            stages[stage]['failed'] += 1

    print("\nStage Statistics:")
    for stage, data in stages.items():
        success_rate = data['success'] / data['count'] * 100 if data['count'] > 0 else 0
        avg_duration = data['total_duration'] / data['count'] if data['count'] > 0 else 0
        print(f"  {stage}:")
        print(f"    Count: {data['count']}")
        print(f"    Success rate: {success_rate:.1f}%")
        print(f"    Average duration: {avg_duration:.2f}s")

    # Calculate storage usage
    print("\nStorage Usage:")
    total_pdf_size = 0
    total_md_size = 0
    paper_count = 0

    papers_dir = storage.papers_dir
    if papers_dir.exists():
        for paper_dir in papers_dir.iterdir():
            if paper_dir.is_dir():
                pdf_path = storage.get_pdf_path(paper_dir.name)
                md_path = storage.get_markdown_path(paper_dir.name)

                if pdf_path.exists():
                    total_pdf_size += pdf_path.stat().st_size
                if md_path.exists():
                    total_md_size += md_path.stat().st_size
                paper_count += 1

    print(f"  Papers processed: {paper_count}")
    print(f"  Total PDF size: {format_bytes(total_pdf_size)}")
    print(f"  Total Markdown size: {format_bytes(total_md_size)}")
    print(f"  Total storage: {format_bytes(total_pdf_size + total_md_size)}")

    print("="*60)

if __name__ == "__main__":
    main()
