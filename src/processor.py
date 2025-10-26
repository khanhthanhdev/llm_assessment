import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

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
        start_time = time.time()

        result = {
            "paper_id": paper_id,
            "status": "pending",
            "errors": [],
            "processing_time_seconds": 0
        }

        logger.info(f"Processing paper: {paper_id} - {paper_data.get('title', 'Unknown')}")

        try:
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

            pdf_start = time.time()
            pdf_content = self.downloader.download(pdf_url, paper_id)
            pdf_duration = time.time() - pdf_start

            if not pdf_content:
                error = "Failed to download PDF"
                logger.error(f"{paper_id}: {error}")
                result['errors'].append(error)
                result['status'] = 'failed_download'

                # Log failed download
                self._log_processing_step(paper_id, 'pdf_download', 'failed', pdf_duration, error=error)
                return result

            # Save PDF
            pdf_info = self.storage.save_pdf(paper_id, pdf_content)
            result['pdf_downloaded'] = True
            result['pdf_size_bytes'] = pdf_info['size_bytes']

            # Log successful download
            self._log_processing_step(paper_id, 'pdf_download', 'success', pdf_duration,
                                    file_size_bytes=pdf_info['size_bytes'])

            # Step 2: Convert to Markdown
            md_start = time.time()
            pdf_path = self.storage.get_pdf_path(paper_id)
            markdown_content = self.converter.convert_pdf_to_markdown(pdf_path, paper_id)
            md_duration = time.time() - md_start

            if not markdown_content:
                error = "Failed to convert PDF to markdown"
                logger.error(f"{paper_id}: {error}")
                result['errors'].append(error)
                result['status'] = 'failed_conversion'

                # Log failed conversion
                self._log_processing_step(paper_id, 'markdown_conversion', 'failed', md_duration, error=error)
                return result

            # Add metadata header
            markdown_with_header = self.converter.add_metadata_header(markdown_content, paper_data)

            # Save markdown
            md_info = self.storage.save_markdown(paper_id, markdown_with_header)
            result['markdown_generated'] = True
            result['markdown_size_bytes'] = md_info['size_bytes']

            # Log successful conversion
            self._log_processing_step(paper_id, 'markdown_conversion', 'success', md_duration)

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
                "markitdown_version": "0.1.0",  # TODO: get actual version
                "conversion_duration_seconds": md_duration,
                "errors": result['errors']
            }

            paper_data['files'] = {
                "pdf": str(self.storage.get_pdf_path(paper_id)),
                "markdown": str(self.storage.get_markdown_path(paper_id)),
                "full_json": str(self.storage.get_json_path(paper_id))
            }

            self.storage.save_paper_json(paper_id, paper_data)

            # Update index
            self.storage.update_index(paper_id, paper_data, 'completed')

            result['status'] = 'completed'
            logger.info(f"Successfully processed paper: {paper_id}")

        except Exception as e:
            error = f"Unexpected error processing {paper_id}: {str(e)}"
            logger.error(error)
            result['errors'].append(error)
            result['status'] = 'failed'
            result['processing_time_seconds'] = time.time() - start_time

            # Log error
            self._log_processing_step(paper_id, 'processing', 'error', time.time() - start_time, error=error)
            return result

        result['processing_time_seconds'] = time.time() - start_time
        return result

    def _log_processing_step(self, paper_id: str, stage: str, status: str,
                           duration_seconds: float, file_size_bytes: int = None, error: str = None):
        """Log a processing step"""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "paper_id": paper_id,
            "stage": stage,
            "status": status,
            "duration_seconds": round(duration_seconds, 2)
        }

        if file_size_bytes:
            entry["file_size_bytes"] = file_size_bytes

        if error:
            entry["error"] = error

        self.storage.append_processing_log(entry)

    def get_processing_stats(self) -> Dict:
        """Get processing statistics"""
        index = self.storage.load_index()
        log_entries = self.storage.load_processing_log()

        stats = {
            'index_stats': index['stats'],
            'total_log_entries': len(log_entries),
            'last_updated': index.get('last_updated')
        }

        return stats
