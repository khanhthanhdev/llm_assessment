# ICLR 2024 Paper Crawler & Processor

This script crawls all ICLR 2024 papers from OpenReview and processes them (downloads PDFs + converts to markdown).

## Prerequisites

1. **OpenReview Credentials**: Set up your OpenReview API credentials
   ```bash
   cp .env.example .env
   # Edit .env with your OpenReview username/password
   ```

2. **Install Dependencies**:
   ```bash
   uv sync
   ```

## Usage

### Option 1: Full Pipeline (Crawl + Process)
Crawl all ICLR 2024 papers and process them:
```bash
uv run python scripts/crawl_and_process_iclr.py
```

### Option 2: Process Existing Data
Use existing crawled data and process it:
```bash
uv run python scripts/crawl_and_process_iclr.py --skip-crawl --input-file iclr_2024_papers_reviews_accepted.json
```

### Option 3: Test with Small Batch
Process only first N papers:
```bash
uv run python scripts/crawl_and_process_iclr.py --limit 10
```

### Option 4: Only Accepted Papers
Crawl and process only accepted papers:
```bash
uv run python scripts/crawl_and_process_iclr.py --accepted-only
```

## Available Options

- `--year YEAR`: ICLR year to crawl (default: 2024)
- `--accepted-only`: Only crawl/process accepted papers
- `--limit LIMIT`: Limit number of papers to process
- `--skip-crawl`: Skip crawling, use existing JSON file
- `--input-file FILE`: Use specific input JSON file

## Output

After processing, each paper will have:
```
data/papers/{paper_id}/
├── paper.pdf          # Downloaded PDF
├── paper.md           # Markdown with metadata header
└── paper_full.json    # Complete data with processing info
```

## Monitoring

- Check processing status: `uv run python scripts/stats.py`
- View logs: `logs/processing_*.log`
- Retry failed papers: `uv run python scripts/retry_failed.py`

## Example Commands

```bash
# Process all ICLR 2024 accepted papers
uv run python scripts/crawl_and_process_iclr.py --accepted-only

# Process first 50 papers from existing data
uv run python scripts/crawl_and_process_iclr.py --skip-crawl --input-file iclr_2024_papers_reviews_accepted.json --limit 50

# Full crawl and process (will take several hours for all papers)
uv run python scripts/crawl_and_process_iclr.py
```
