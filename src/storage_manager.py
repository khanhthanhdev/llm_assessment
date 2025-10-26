import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class StorageManager:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.papers_dir = self.base_dir / "papers"
        self.index_dir = self.base_dir / "index"
        self.input_dir = self.base_dir / "input"

        # Create directories
        self.papers_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.input_dir.mkdir(parents=True, exist_ok=True)

    def get_paper_dir(self, paper_id: str) -> Path:
        """Get directory path for a specific paper"""
        return self.papers_dir / paper_id

    def get_pdf_path(self, paper_id: str) -> Path:
        """Get PDF file path for a paper"""
        return self.get_paper_dir(paper_id) / "paper.pdf"

    def get_markdown_path(self, paper_id: str) -> Path:
        """Get markdown file path for a paper"""
        return self.get_paper_dir(paper_id) / "paper.md"

    def get_json_path(self, paper_id: str) -> Path:
        """Get JSON file path for a paper"""
        return self.get_paper_dir(paper_id) / "paper_full.json"

    def get_index_path(self) -> Path:
        """Get papers index file path"""
        return self.index_dir / "papers_index.json"

    def get_log_path(self) -> Path:
        """Get processing log file path"""
        return self.index_dir / "processing_log.json"

    def paper_exists(self, paper_id: str) -> Dict[str, bool]:
        """Check if paper files exist"""
        paper_dir = self.get_paper_dir(paper_id)
        return {
            'dir': paper_dir.exists(),
            'pdf': self.get_pdf_path(paper_id).exists(),
            'markdown': self.get_markdown_path(paper_id).exists(),
            'json': self.get_json_path(paper_id).exists()
        }

    def save_pdf(self, paper_id: str, content: bytes) -> Dict:
        """Save PDF content and return file info"""
        paper_dir = self.get_paper_dir(paper_id)
        paper_dir.mkdir(exist_ok=True)

        pdf_path = self.get_pdf_path(paper_id)
        with open(pdf_path, 'wb') as f:
            f.write(content)

        # Calculate checksum
        checksum = hashlib.sha256(content).hexdigest()
        size_bytes = len(content)

        return {
            'path': pdf_path,
            'size_bytes': size_bytes,
            'checksum': f"sha256:{checksum}"
        }

    def save_markdown(self, paper_id: str, content: str) -> Dict:
        """Save markdown content and return file info"""
        paper_dir = self.get_paper_dir(paper_id)
        paper_dir.mkdir(exist_ok=True)

        md_path = self.get_markdown_path(paper_id)
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(content)

        size_bytes = len(content.encode('utf-8'))

        return {
            'path': md_path,
            'size_bytes': size_bytes
        }

    def save_paper_json(self, paper_id: str, data: Dict):
        """Save complete paper data as JSON"""
        paper_dir = self.get_paper_dir(paper_id)
        paper_dir.mkdir(exist_ok=True)

        json_path = self.get_json_path(paper_id)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_paper_json(self, paper_id: str) -> Optional[Dict]:
        """Load paper data from JSON file"""
        json_path = self.get_json_path(paper_id)
        if not json_path.exists():
            return None

        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_index(self) -> Dict:
        """Load papers index"""
        index_path = self.get_index_path()
        if not index_path.exists():
            return {
                'total_papers': 0,
                'last_updated': None,
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

        with open(index_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_index(self, index_data: Dict):
        """Save papers index"""
        index_path = self.get_index_path()
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)

    def update_index(self, paper_id: str, paper_data: Dict, status: str):
        """Update index with paper information"""
        index = self.load_index()

        # Update paper entry
        index['papers'][paper_id] = {
            'title': paper_data.get('title', ''),
            'authors': paper_data.get('authors', []),
            'pdf_url': paper_data.get('pdf_url', ''),
            'status': status,
            'has_pdf': (status in ['completed', 'pdf_downloaded']),
            'has_markdown': (status == 'completed'),
            'decision': paper_data.get('decision', '')
        }

        # Update stats
        stats = index['stats']
        stats['total'] = len(index['papers'])

        # Recalculate stats
        status_counts = {}
        for paper in index['papers'].values():
            status_counts[paper['status']] = status_counts.get(paper['status'], 0) + 1

        stats.update({
            'completed': status_counts.get('completed', 0),
            'pdf_downloaded': status_counts.get('pdf_downloaded', 0) + status_counts.get('completed', 0),
            'markdown_generated': status_counts.get('completed', 0),
            'failed_download': status_counts.get('failed_download', 0),
            'failed_conversion': status_counts.get('failed_conversion', 0),
            'pending': status_counts.get('pending', 0)
        })

        index['last_updated'] = paper_data.get('processing', {}).get('markdown_generated_at', None)

        self.save_index(index)

    def load_processing_log(self) -> List[Dict]:
        """Load processing log entries"""
        log_path = self.get_log_path()
        if not log_path.exists():
            return []

        with open(log_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('log_entries', [])

    def append_processing_log(self, entry: Dict):
        """Append entry to processing log"""
        log_data = {
            'log_entries': self.load_processing_log()
        }
        log_data['log_entries'].append(entry)

        log_path = self.get_log_path()
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
