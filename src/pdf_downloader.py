import requests
import time
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class PDFDownloader:
    def __init__(self, timeout: int = 60, max_retries: int = 3,
                 retry_delay: int = 5, user_agent: str = "OpenReview-Crawler/1.0"):
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': user_agent})

    def download(self, url: str, paper_id: str) -> Optional[bytes]:
        """Download PDF from URL with retry logic"""

        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"Downloading PDF for {paper_id} from {url} (attempt {attempt + 1})")

                response = self.session.get(url, timeout=self.timeout, stream=True)
                response.raise_for_status()

                # Check content type
                content_type = response.headers.get('content-type', '').lower()
                if 'pdf' not in content_type:
                    logger.warning(f"Unexpected content type for {paper_id}: {content_type}")

                # Download content
                content = response.content

                if len(content) == 0:
                    logger.error(f"Empty content received for {paper_id}")
                    return None

                logger.info(f"Successfully downloaded PDF for {paper_id} ({len(content)} bytes)")
                return content

            except requests.exceptions.RequestException as e:
                logger.warning(f"Download attempt {attempt + 1} failed for {paper_id}: {e}")

                if attempt < self.max_retries:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"All download attempts failed for {paper_id}")
                    return None

            except Exception as e:
                logger.error(f"Unexpected error downloading {paper_id}: {e}")
                return None

    def download_with_progress(self, url: str, paper_id: str, chunk_size: int = 8192) -> Optional[bytes]:
        """Download PDF with progress tracking (for large files)"""
        try:
            logger.info(f"Downloading PDF for {paper_id} from {url}")

            response = self.session.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            content = b''

            if total_size > 0:
                logger.info(f"Downloading {total_size} bytes for {paper_id}")

            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    content += chunk

            if len(content) == 0:
                logger.error(f"Empty content received for {paper_id}")
                return None

            logger.info(f"Successfully downloaded PDF for {paper_id} ({len(content)} bytes)")
            return content

        except Exception as e:
            logger.error(f"Error downloading {paper_id}: {e}")
            return None
