"""
OCR + Metadata Extractor (D14)
Extracts text from PDFs and parses certificate metadata
"""

import logging
import re
from datetime import datetime
from typing import Any

import pytesseract
from pdf2image import convert_from_path

logger = logging.getLogger(__name__)


class CertificateMetadataExtractor:
    """Extract structured metadata from certificate documents"""

    def __init__(self):
        self.date_patterns = [
            r"\d{1,2}/\d{1,2}/\d{4}",  # MM/DD/YYYY
            r"\d{4}-\d{2}-\d{2}",  # YYYY-MM-DD
            r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}",  # Month DD, YYYY
        ]

        self.agency_patterns = [
            r"(?:issued by|issuing agency):?\s*([^\n]+)",
            r"(.*?(?:health department|health dept|board of health).*?)(?:\n|$)",
            r"(.*?(?:county|city|state).*?(?:office|bureau|department).*?)(?:\n|$)",
        ]

    def extract_from_pdf(self, pdf_path: str) -> dict[str, Any]:
        """
        Extract text and metadata from PDF certificate

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with extracted text and parsed metadata
        """
        try:
            # Convert PDF to images
            images = convert_from_path(pdf_path, dpi=300)

            # OCR each page
            full_text = ""
            for _i, image in enumerate(images):
                text = pytesseract.image_to_string(image, lang="eng")
                full_text += text + "\n"

            logger.info(f"Extracted {len(full_text)} characters from {len(images)} pages")

            # Parse metadata
            metadata = self._parse_metadata(full_text)
            metadata["page_count"] = len(images)
            metadata["raw_text"] = full_text

            return metadata

        except Exception as e:
            logger.error(f"Failed to extract from PDF: {e}")
            return {"error": str(e), "raw_text": "", "page_count": 0}

    def _parse_metadata(self, text: str) -> dict[str, Any]:
        """Parse structured metadata from extracted text"""

        metadata = {
            "dates_found": [],
            "issuing_agency": None,
            "owner_name": None,
            "certificate_number": None,
            "expiration_date": None,
            "issue_date": None,
        }

        # Extract dates
        for pattern in self.date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            metadata["dates_found"].extend(matches)

        # Parse expiration date (usually labeled)
        exp_match = re.search(
            r"(?:expir(?:ation|es)|valid until|expires on):?\s*([0-9/\-]+)", text, re.IGNORECASE
        )
        if exp_match:
            metadata["expiration_date"] = self._normalize_date(exp_match.group(1))

        # Parse issue date
        issue_match = re.search(
            r"(?:issue date|issued on|date issued):?\s*([0-9/\-]+)", text, re.IGNORECASE
        )
        if issue_match:
            metadata["issue_date"] = self._normalize_date(issue_match.group(1))

        # Extract issuing agency
        for pattern in self.agency_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata["issuing_agency"] = match.group(1).strip()
                break

        # Extract owner/holder name (usually after "issued to" or at top)
        name_match = re.search(
            r"(?:issued to|name|holder):?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", text
        )
        if name_match:
            metadata["owner_name"] = name_match.group(1).strip()

        # Extract certificate number
        cert_num_match = re.search(
            r"(?:certificate|permit|license)\s*(?:no|number|#):?\s*([A-Z0-9\-]+)",
            text,
            re.IGNORECASE,
        )
        if cert_num_match:
            metadata["certificate_number"] = cert_num_match.group(1).strip()

        return metadata

    def _normalize_date(self, date_str: str) -> str | None:
        """Normalize date to ISO format"""
        formats = ["%m/%d/%Y", "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.isoformat()
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_str}")
        return date_str  # Return as-is if can't parse


# Mock implementation for testing (when Tesseract not available)
class MockExtractor:
    """Mock extractor for testing without Tesseract"""

    def extract_from_pdf(self, pdf_path: str) -> dict[str, Any]:
        """Mock extraction returning sample data"""
        return {
            "raw_text": """
                HEALTH PERMIT
                Certificate Number: HP-2024-12345
                Issued to: John Doe
                Issuing Agency: County Health Department
                Issue Date: 01/15/2024
                Expiration Date: 01/15/2025

                This permit authorizes the operation of a food establishment.
                Signed by: Health Inspector Jane Smith
            """,
            "dates_found": ["01/15/2024", "01/15/2025"],
            "issuing_agency": "County Health Department",
            "owner_name": "John Doe",
            "certificate_number": "HP-2024-12345",
            "expiration_date": "2025-01-15T00:00:00",
            "issue_date": "2024-01-15T00:00:00",
            "page_count": 1,
        }


# Factory function
def get_extractor() -> CertificateMetadataExtractor:
    """Get appropriate extractor based on environment"""
    try:
        # Test if Tesseract is available
        pytesseract.get_tesseract_version()
        return CertificateMetadataExtractor()
    except:
        logger.warning("Tesseract not available, using mock extractor")
        return MockExtractor()


if __name__ == "__main__":
    # Test with sample PDF
    extractor = get_extractor()
    result = extractor.extract_from_pdf("sample_certificate.pdf")

    import json

    print(json.dumps(result, indent=2))
