#!/usr/bin/env python3
import json
import yaml
from pathlib import Path
import sys
from tqdm import tqdm
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage_manager import StorageManager

def load_config():
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def rebuild_index(config):
    """Rebuild the papers index from existing files"""
    storage = StorageManager(config['storage']['base_dir'])

    print("Rebuilding papers index...")

    # Start with empty index
    index = {
        'total_papers': 0,
        'last_updated': datetime.utcnow().isoformat() + "Z",
        'papers': {},
        'stats': {
            'total': 0,
            'completed': 0,
            'pdf_downloaded': 0,
            'markdown_generated': 0,
            'failed_download': 0,
            'failed_conversion': 0,
            'pending': 0
        }
    }

    papers_dir = storage.papers_dir
    if not papers_dir.exists():
        print(f"Papers directory does not exist: {papers_dir}")
        return

    # Scan existing paper directories
    paper_dirs = list(papers_dir.iterdir())
    paper_dirs = [d for d in paper_dirs if d.is_dir()]

    print(f"Found {len(paper_dirs)} paper directories")

    for paper_dir in tqdm(paper_dirs, desc="Scanning papers"):
        paper_id = paper_dir.name

        # Check what files exist
        exists = storage.paper_exists(paper_id)

        # Try to load paper data
        paper_data = storage.load_paper_json(paper_id)

        if paper_data:
            # Use data from JSON file
            status = paper_data.get('processing', {}).get('status', 'unknown')
            title = paper_data.get('title', '')
            authors = paper_data.get('authors', [])
            pdf_url = paper_data.get('pdf_url', '')
            decision = paper_data.get('decision', '')
        else:
            # Infer status from files
            if exists['markdown']:
                status = 'completed'
            elif exists['pdf']:
                status = 'pdf_downloaded'
            else:
                status = 'unknown'

            title = paper_id  # Use ID as fallback
            authors = []
            pdf_url = ''
            decision = ''

        # Update index
        index['papers'][paper_id] = {
            'title': title,
            'authors': authors,
            'pdf_url': pdf_url,
            'status': status,
            'has_pdf': exists['pdf'],
            'has_markdown': exists['markdown'],
            'decision': decision
        }

    # Calculate stats
    status_counts = {}
    for paper in index['papers'].values():
        status_counts[paper['status']] = status_counts.get(paper['status'], 0) + 1

    stats = index['stats']
    stats['total'] = len(index['papers'])
    stats['completed'] = status_counts.get('completed', 0)
    stats['pdf_downloaded'] = status_counts.get('pdf_downloaded', 0) + stats['completed']
    stats['markdown_generated'] = stats['completed']
    # Note: failed counts can't be determined from filesystem scan

    # Save index
    storage.save_index(index)

    print("
Index rebuilt:"    print(f"  Total papers: {stats['total']}")
    print(f"  Completed: {stats['completed']}")
    print(f"  PDFs only: {status_counts.get('pdf_downloaded', 0)}")
    print(f"  Unknown status: {status_counts.get('unknown', 0)}")

    print(f"Index saved to: {storage.get_index_path()}")

def main():
    config = load_config()
    rebuild_index(config)

if __name__ == "__main__":
    main()
