# OpenReview Paper Crawler with MarkItDown

## Project Overview
A system to crawl papers from OpenReview, download PDFs using the `pdf_url` from JSON metadata, and convert them to markdown using MarkItDown library.

---

## Folder Structure

```
open_review/
├── data/
│   ├── papers/
│   │   └── {paper_id}/
│   │       ├── paper.pdf                    # Original PDF from OpenReview
│   │       ├── paper.md                     # Markdown (converted via MarkItDown)
│   │       └── paper_full.json             # Complete paper data
│   │
│   ├── index/
│   │   ├── papers_index.json               # Index of all papers with status
│   │   └── processing_log.json             # Processing history and errors
│   │
│   └── input/
│       └── iclr_2024_papers_reviews_accepted.json  # Input JSON from OpenReview
│
├── src/
│   ├── __init__.py
│   ├── pdf_downloader.py                    # Download PDFs from pdf_url
│   ├── markdown_converter.py                # MarkItDown wrapper
│   ├── storage_manager.py                   # File/JSON storage handler
│   └── processor.py                         # Main processing pipeline
│
├── scripts/
│   ├── process_papers.py                    # Main script to process all papers
│   ├── retry_failed.py                      # Retry failed conversions
│   ├── rebuild_index.py                     # Rebuild index
│   └── stats.py                             # Show processing statistics
│
├── config.yaml                              # Configuration file (in root)
│
├── logs/
│   └── processing_{timestamp}.log
│
├── tests/
│   ├── test_downloader.py
│   ├── test_converter.py
│   └── test_storage.py
│
├── pyproject.toml                          # Dependencies (using uv)
├── uv.lock
├── README.md
├── .env
├── get_url.py                              # Existing URL utility
├── main.py                                 # Existing main script
└── iclr_2024_papers_reviews_accepted.json   # Existing input data
```

---

## Data Schema

### 1. Input: `iclr_2024_papers_reviews_accepted.json`

Your existing JSON with OpenReview data:

```json
[
  {
    "paper_id": "abc123xyz",
    "forum_id": "forum_xyz",
    "number": 42,
    "title": "Novel Approach to Machine Learning",
    "abstract": "We present...",
    "authors": ["Alice Smith", "Bob Jones"],
    "keywords": ["machine learning", "optimization"],
    "pdf_url": "https://openreview.net/pdf?id=abc123xyz",
    "forum_url": "https://openreview.net/forum?id=abc123xyz",
    "reviews": [...],
    "comments": [...],
    "meta_reviews": [...],
    "decision": "Accept (Poster)"
  }
]
```

### 2. Output: `paper_full.json` (per paper)

Enhanced with processing metadata:

```json
{
  "paper_id": "abc123xyz",
  "forum_id": "forum_xyz",
  "number": 42,
  "title": "Novel Approach to Machine Learning",
  "abstract": "We present...",
  "authors": ["Alice Smith", "Bob Jones"],
  "keywords": ["machine learning", "optimization"],
  "pdf_url": "https://openreview.net/pdf?id=abc123xyz",
  "forum_url": "https://openreview.net/forum?id=abc123xyz",
  
  "reviews": [
    {
      "review_id": "review_001",
      "rating": 8,
      "confidence": 4,
      "summary": "This paper proposes...",
      "soundness": 4,
      "presentation": 3,
      "contribution": 4,
      "strengths": "Novel approach...",
      "weaknesses": "Limited experiments...",
      "questions": "How does this compare...",
      "limitations": "The authors acknowledge...",
      "created": 1698765432000,
      "modified": 1698765432000
    }
  ],
  
  "comments": [
    {
      "id": "comment_001",
      "replyto": "review_001",
      "content": "Thank you for the feedback...",
      "created": 1698765432000
    }
  ],
  
  "meta_reviews": [...],
  "decision": "Accept (Poster)",
  
  "processing": {
    "status": "completed",
    "pdf_downloaded": true,
    "pdf_downloaded_at": "2025-10-25T10:25:00Z",
    "pdf_size_bytes": 1048576,
    "pdf_checksum": "sha256:abc123...",
    "markdown_generated": true,
    "markdown_generated_at": "2025-10-25T10:26:00Z",
    "markdown_size_bytes": 85432,
    "markitdown_version": "0.1.0",
    "conversion_duration_seconds": 8.5,
    "errors": []
  },
  
  "files": {
    "pdf": "papers/abc123xyz/paper.pdf",
    "markdown": "papers/abc123xyz/paper.md",
    "full_json": "papers/abc123xyz/paper_full.json"
  }
}
```

### 3. `papers_index.json` - Quick Lookup

```json
{
  "total_papers": 1523,
  "last_updated": "2025-10-25T12:00:00Z",
  "papers": {
    "abc123xyz": {
      "title": "Novel Approach to Machine Learning",
      "authors": ["Alice Smith", "Bob Jones"],
      "pdf_url": "https://openreview.net/pdf?id=abc123xyz",
      "status": "completed",
      "has_pdf": true,
      "has_markdown": true,
      "decision": "Accept (Poster)"
    }
  },
  "stats": {
    "total": 1523,
    "completed": 1450,
    "pdf_downloaded": 1498,
    "markdown_generated": 1450,
    "failed_download": 25,
    "failed_conversion": 48,
    "pending": 0
  }
}
```

### 4. `processing_log.json` - Processing History

```json
{
  "log_entries": [
    {
      "timestamp": "2025-10-25T10:25:00Z",
      "paper_id": "abc123xyz",
      "stage": "pdf_download",
      "status": "success",
      "duration_seconds": 3.2,
      "file_size_bytes": 1048576
    },
    {
      "timestamp": "2025-10-25T10:26:00Z",
      "paper_id": "abc123xyz",
      "stage": "markdown_conversion",
      "status": "success",
      "duration_seconds": 8.5
    },
    {
      "timestamp": "2025-10-25T10:30:00Z",
      "paper_id": "def456uvw",
      "stage": "pdf_download",
      "status": "failed",
      "error": "HTTP 404: PDF not found",
      "retry_count": 3
    }
  ]
}
```

---

## Implementation Files

### 1. `pyproject.toml` (Dependencies)

```toml
[project]
name = "open-review-crawler"
version = "0.1.0"
dependencies = [
    "markitdown>=0.1.0",
    "requests>=2.31.0",
    "python-dotenv>=1.0.0",
    "pyyaml>=6.0.1",
    "tqdm>=4.66.0",
]
```

### 2. `config.yaml`

```yaml
download:
  timeout: 60
  max_retries: 3
  retry_delay: 5
  user_agent: "OpenReview-Crawler/1.0"
  rate_limit: 5  # requests per second
  
storage:
  base_dir: "data"
  input_json: "iclr_2024_papers_reviews_accepted.json"
  
conversion:
  markitdown_options: {}
  skip_existing: true
  
processing:
  batch_size: 10
  parallel_workers: 4
  resume_on_restart: true
  
logging:
  level: "INFO"
  file: "logs/processing.log"
  console: true
```

---

## Key Python Files

### `src/storage_manager.py`

```python
from pathlib import Path
import json
import hashlib
from typing import Dict, Optional

class StorageManager:
    def __init__(self, base_dir: str = "data"):
        self.base_dir = Path(base_dir)
        self.papers_dir = self.base_dir / "papers"
        self.index_dir = self.base_dir / "index"
        
        # Create directories
        self.papers_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)
    
    def get_paper_dir(self, paper_id: str) -> Path:
        paper_dir = self.papers_dir / paper_id
        paper_dir.mkdir(exist_ok=True)
        return paper_dir
    
    def get_pdf_path(self, paper_id: str) -> Path:
        return self.get_paper_dir(paper_id) / "paper.pdf"
    
    def get_markdown_path(self, paper_id: str) -> Path:
        return self.get_paper_dir(paper_id) / "paper.md"
    
    def get_json_path(self, paper_id: str) -> Path:
        return self.get_paper_dir(paper_id) / "paper_full.json"
    
    def save_pdf(self, paper_id: str, pdf_content: bytes) -> Dict:
        pdf_path = self.get_pdf_path(paper_id)
        pdf_path.write_bytes(pdf_content)
        
        # Calculate checksum
        checksum = hashlib.sha256(pdf_content).hexdigest()
        
        return {
            "path": str(pdf_path),
            "size_bytes": len(pdf_content),
            "checksum": f"sha256:{checksum}"
        }
    
    def save_markdown(self, paper_id: str, markdown_content: str) -> Dict:
        md_path = self.get_markdown_path(paper_id)
        md_path.write_text(markdown_content, encoding='utf-8')
        
        return {
            "path": str(md_path),
            "size_bytes": len(markdown_content.encode('utf-8'))
        }
    
    def save_paper_json(self, paper_id: str, data: Dict):
        json_path = self.get_json_path(paper_id)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_paper_json(self, paper_id: str) -> Optional[Dict]:
        json_path = self.get_json_path(paper_id)
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def paper_exists(self, paper_id: str) -> Dict[str, bool]:
        return {
            "pdf": self.get_pdf_path(paper_id).exists(),
            "markdown": self.get_markdown_path(paper_id).exists(),
            "json": self.get_json_path(paper_id).exists()
        }
```

### `src/pdf_downloader.py`

```python
import requests
import time
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class PDFDownloader:
    def __init__(self, timeout: int = 60, max_retries: int = 3, 
                 retry_delay: int = 5, user_agent: str = None):
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session = requests.Session()
        
        if user_agent:
            self.session.headers['User-Agent'] = user_agent
    
    def download(self, pdf_url: str, paper_id: str) -> Optional[bytes]:
        """Download PDF from URL with retries"""
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Downloading PDF for {paper_id} (attempt {attempt}/{self.max_retries})")
                logger.debug(f"URL: {pdf_url}")
                
                response = self.session.get(pdf_url, timeout=self.timeout)
                response.raise_for_status()
                
                # Verify it's a PDF
                content_type = response.headers.get('Content-Type', '')
                if 'pdf' not in content_type.lower():
                    logger.warning(f"URL did not return PDF. Content-Type: {content_type}")
                
                logger.info(f"Successfully downloaded PDF for {paper_id} ({len(response.content)} bytes)")
                return response.content
                
            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP error downloading {paper_id}: {e}")
                if e.response.status_code == 404:
                    logger.error(f"PDF not found (404) for {paper_id}")
                    return None  # Don't retry 404s
                    
            except requests.exceptions.Timeout:
                logger.error(f"Timeout downloading {paper_id}")
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error downloading {paper_id}: {e}")
            
            # Wait before retry
            if attempt < self.max_retries:
                logger.info(f"Retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)
        
        logger.error(f"Failed to download PDF for {paper_id} after {self.max_retries} attempts")
        return None
```

### `src/markdown_converter.py`

```python
from markitdown import MarkItDown
from pathlib import Path
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class MarkdownConverter:
    def __init__(self):
        self.converter = MarkItDown()
    
    def convert_pdf_to_markdown(self, pdf_path: Path, paper_id: str) -> Optional[str]:
        """Convert PDF to markdown using MarkItDown"""
        
        try:
            logger.info(f"Converting PDF to markdown for {paper_id}")
            
            # Convert using MarkItDown
            result = self.converter.convert(str(pdf_path))
            
            if result and result.text_content:
                markdown_content = result.text_content
                logger.info(f"Successfully converted {paper_id} to markdown ({len(markdown_content)} chars)")
                return markdown_content
            else:
                logger.error(f"MarkItDown returned empty content for {paper_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error converting {paper_id} to markdown: {e}")
            return None
    
    def add_metadata_header(self, markdown: str, paper_data: Dict) -> str:
        """Add paper metadata as YAML frontmatter"""
        
        header = "---\n"
        header += f"paper_id: {paper_data.get('paper_id', 'unknown')}\n"
        header += f"title: \"{paper_data.get('title', 'Unknown')}\"\n"
        
        authors = paper_data.get('authors', [])
        if authors:
            header += "authors:\n"
            for author in authors:
                header += f"  - {author}\n"
        
        keywords = paper_data.get('keywords', [])
        if keywords:
            header += "keywords:\n"
            for keyword in keywords:
                header += f"  - {keyword}\n"
        
        header += f"pdf_url: {paper_data.get('pdf_url', '')}\n"
        header += f"forum_url: {paper_data.get('forum_url', '')}\n"
        header += f"decision: {paper_data.get('decision', 'Unknown')}\n"
        header += "---\n\n"
        
        return header + markdown
```

### `src/processor.py`

```python
import logging
from datetime import datetime
from typing import Dict, List
from pathlib import Path
import json

from .storage_manager import StorageManager
from .pdf_downloader import PDFDownloader
from .markdown_converter import MarkdownConverter

logger = logging.getLogger(__name__)

class PaperProcessor:
    def __init__(self, config: Dict):
        self.config = config
        self.storage = StorageManager(config['storage']['base_dir'])
        self.downloader = PDFDownloader(
            timeout=config['download']['timeout'],
            max_retries=config['download']['max_retries'],
            retry_delay=config['download']['retry_delay'],
            user_agent=config['download']['user_agent']
        )
        self.converter = MarkdownConverter()
    
    def process_paper(self, paper_data: Dict) -> Dict:
        """Process a single paper: download PDF and convert to markdown"""
        
        paper_id = paper_data['paper_id']
        result = {
            "paper_id": paper_id,
            "status": "pending",
            "errors": []
        }
        
        logger.info(f"Processing paper: {paper_id} - {paper_data.get('title', 'Unknown')}")
        
        # Check if already processed
        if self.config['conversion']['skip_existing']:
            exists = self.storage.paper_exists(paper_id)
            if exists['pdf'] and exists['markdown']:
                logger.info(f"Paper {paper_id} already processed, skipping")
                result['status'] = 'skipped'
                return result
        
        # Step 1: Download PDF
        pdf_url = paper_data.get('pdf_url')
        if not pdf_url:
            error = "No pdf_url in paper data"
            logger.error(f"{paper_id}: {error}")
            result['errors'].append(error)
            result['status'] = 'failed'
            return result
        
        pdf_content = self.downloader.download(pdf_url, paper_id)
        if not pdf_content:
            error = "Failed to download PDF"
            logger.error(f"{paper_id}: {error}")
            result['errors'].append(error)
            result['status'] = 'failed_download'
            return result
        
        # Save PDF
        pdf_info = self.storage.save_pdf(paper_id, pdf_content)
        result['pdf_downloaded'] = True
        result['pdf_size_bytes'] = pdf_info['size_bytes']
        
        # Step 2: Convert to Markdown
        pdf_path = self.storage.get_pdf_path(paper_id)
        markdown_content = self.converter.convert_pdf_to_markdown(pdf_path, paper_id)
        
        if not markdown_content:
            error = "Failed to convert PDF to markdown"
            logger.error(f"{paper_id}: {error}")
            result['errors'].append(error)
            result['status'] = 'failed_conversion'
            return result
        
        # Add metadata header
        markdown_with_header = self.converter.add_metadata_header(markdown_content, paper_data)
        
        # Save markdown
        md_info = self.storage.save_markdown(paper_id, markdown_with_header)
        result['markdown_generated'] = True
        result['markdown_size_bytes'] = md_info['size_bytes']
        
        # Step 3: Save complete JSON with processing info
        paper_data['processing'] = {
            "status": "completed",
            "pdf_downloaded": True,
            "pdf_downloaded_at": datetime.utcnow().isoformat() + "Z",
            "pdf_size_bytes": pdf_info['size_bytes'],
            "pdf_checksum": pdf_info['checksum'],
            "markdown_generated": True,
            "markdown_generated_at": datetime.utcnow().isoformat() + "Z",
            "markdown_size_bytes": md_info['size_bytes'],
            "errors": result['errors']
        }
        
        paper_data['files'] = {
            "pdf": str(pdf_path),
            "markdown": str(self.storage.get_markdown_path(paper_id)),
            "full_json": str(self.storage.get_json_path(paper_id))
        }
        
        self.storage.save_paper_json(paper_id, paper_data)
        
        result['status'] = 'completed'
        logger.info(f"Successfully processed paper: {paper_id}")
        
        return result
```

---

## Main Script: `scripts/process_papers.py`

```python
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
    
    # Save processing log
    log_path = Path(config['storage']['base_dir']) / "index" / "processing_log.json"
    with open(log_path, 'w') as f:
        json.dump({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_papers": len(papers),
            "results": results
        }, f, indent=2)
    
    logger.info(f"Processing log saved to: {log_path}")

if __name__ == "__main__":
    main()
```

---

## Usage

### 1. Install Dependencies
```bash
uv sync
```

### 2. Prepare Input JSON
Your OpenReview JSON is already at: `iclr_2024_papers_reviews_accepted.json`

### 3. Run Processing
```bash
uv run python scripts/process_papers.py
```

### 4. Monitor Progress
Check logs at: `logs/processing.log`

### 5. Retry Failed Papers
```bash
uv run python scripts/retry_failed.py
```

### 6. Check Statistics
```bash
uv run python scripts/stats.py
```

---

## Output Structure

After processing, each paper will have:
```
data/papers/{paper_id}/
├── paper.pdf          # Downloaded PDF
├── paper.md           # Markdown with metadata header
└── paper_full.json    # Complete data with processing info

Index files:
├── data/index/papers_index.json    # Index of all papers with status
└── data/index/processing_log.json  # Processing history and errors
```

---

## Implementation Status

✅ **Complete Implementation**
- Core modules created: `storage_manager.py`, `pdf_downloader.py`, `markdown_converter.py`, `processor.py`
- Main processing script: `scripts/process_papers.py`
- Utility scripts: `retry_failed.py`, `rebuild_index.py`, `stats.py`
- Configuration: `config.yaml`
- Dependencies: `pyproject.toml` with uv support

## Next Steps

1. **Test the implementation**: Run `python scripts/stats.py` to verify setup
2. **Process papers**: Execute `python scripts/process_papers.py` to start crawling
3. **Monitor progress**: Use `python scripts/stats.py` to check processing status
4. **Handle failures**: Run `python scripts/retry_failed.py` for failed papers
5. **Future enhancements**:
   - Add parallel processing for faster downloads
   - Implement citation extraction from markdown
   - Add web interface for monitoring
   - Support for incremental updates