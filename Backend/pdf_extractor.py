from io import BytesIO

from pypdf import PdfReader


def extract_text_from_pdf(pdf_content: bytes) -> str:
    """
    Extract readable text from a PDF.

    Args:
        pdf_content: Raw PDF bytes.

    Returns:
        The extracted text as a single string.

    Raises:
        ValueError: If the PDF cannot be read or contains no extractable text.
    """
    if not pdf_content:
        raise ValueError("PDF content is empty")

    try:
        reader = PdfReader(BytesIO(pdf_content))
        pages = []

        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages.append(text.strip())

        extracted_text = "\n\n".join(pages).strip()

        if not extracted_text:
            raise ValueError(
                "Could not extract text from PDF. "
                "The PDF may contain scanned images instead of selectable text."
            )

        return extracted_text

    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Failed to read PDF: {exc}") from exc
