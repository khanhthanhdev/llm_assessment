import logging
from pathlib import Path
from typing import Optional, Dict, Any
from markitdown import MarkItDown

logger = logging.getLogger(__name__)

class MarkdownConverter:
    def __init__(self):
        self.markitdown = MarkItDown()

    def convert_pdf_to_markdown(self, pdf_path: Path, paper_id: str) -> Optional[str]:
        """Convert PDF file to markdown using MarkItDown"""
        try:
            logger.info(f"Converting PDF to markdown for {paper_id}")

            if not pdf_path.exists():
                logger.error(f"PDF file not found: {pdf_path}")
                return None

            # Convert PDF to markdown
            result = self.markitdown.convert(str(pdf_path))

            if not result or not result.text_content:
                logger.error(f"MarkItDown conversion failed for {paper_id}")
                return None

            markdown_content = result.text_content.strip()

            if len(markdown_content) == 0:
                logger.error(f"Empty markdown content for {paper_id}")
                return None

            logger.info(f"Successfully converted PDF to markdown for {paper_id} ({len(markdown_content)} chars)")
            return markdown_content

        except Exception as e:
            logger.error(f"Error converting PDF for {paper_id}: {e}")
            return None

    def add_metadata_header(self, markdown_content: str, paper_data: Dict[str, Any]) -> str:
        """Add metadata header to markdown content"""
        header_lines = [
            "---",
            f"title: \"{paper_data.get('title', 'Unknown Title')}\"",
            f"authors: {paper_data.get('authors', [])}",
            f"paper_id: {paper_data.get('paper_id', '')}",
            f"forum_id: {paper_data.get('forum_id', '')}",
            f"abstract: \"{paper_data.get('abstract', '')}\"",
            f"keywords: {paper_data.get('keywords', [])}",
            f"pdf_url: {paper_data.get('pdf_url', '')}",
            f"forum_url: {paper_data.get('forum_url', '')}",
            f"decision: \"{paper_data.get('decision', '')}\"",
        ]

        # Add reviews summary if available
        reviews = paper_data.get('reviews', [])
        if reviews:
            header_lines.append(f"num_reviews: {len(reviews)}")
            ratings = [r.get('rating', 0) for r in reviews if r.get('rating')]
            if ratings:
                avg_rating = sum(ratings) / len(ratings)
                header_lines.append(f"average_rating: {avg_rating:.1f}")

        header_lines.append("---")
        header_lines.append("")  # Empty line after header

        header = "\n".join(header_lines)
        return header + "\n" + markdown_content

    def extract_metadata_from_markdown(self, markdown_content: str) -> Dict[str, Any]:
        """Extract metadata from markdown header (for validation)"""
        lines = markdown_content.split('\n')
        metadata = {}

        if not lines or lines[0] != '---':
            return metadata

        in_header = True
        for line in lines[1:]:
            if line == '---':
                break
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                # Try to parse as JSON-like structures
                if value.startswith('[') and value.endswith(']'):
                    # List
                    try:
                        metadata[key] = eval(value)
                    except:
                        metadata[key] = value
                elif value.startswith('"') and value.endswith('"'):
                    # Quoted string
                    metadata[key] = value[1:-1]
                else:
                    # Try to convert to number
                    try:
                        if '.' in value:
                            metadata[key] = float(value)
                        else:
                            metadata[key] = int(value)
                    except ValueError:
                        metadata[key] = value

        return metadata
