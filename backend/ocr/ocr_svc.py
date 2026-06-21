import os
import io
import logging
from pypdf import PdfReader
from PIL import Image
import pytesseract
from google.cloud import vision

from core.config import settings
from ai.gemini_ai import GeminiAIService

logger = logging.getLogger("ecopilot.ocr")


class OCRService:
    """
    Handles optical character recognition (OCR) and text extraction from utility bills.
    Supports direct PDF text extraction, Google Cloud Vision OCR, Tesseract OCR, and Gemini multimodal.
    """
    def __init__(self):
        creds_path = settings.google_application_credentials
        if creds_path and os.path.exists(creds_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
            self.has_vision_creds = True
            logger.info("Google Vision credentials loaded for OCR Service.")
        else:
            self.has_vision_creds = False
            logger.warning("Google Vision credentials missing. Will bypass Google Vision OCR.")

    def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """Extracts text directly from digital PDF pages using pypdf."""
        logger.info("Extracting text directly from digital PDF...")
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            logger.info(f"Direct PDF text extraction complete. Extracted {len(text)} characters.")
            return text
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            return ""

    async def google_vision_ocr(self, image_bytes: bytes) -> str:
        """Extracts text from images using Google Cloud Vision API."""
        if not self.has_vision_creds:
            raise RuntimeError("Google Vision credentials not configured.")

        logger.info("Running Google Cloud Vision OCR...")
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_bytes)
        
        response = client.text_detection(image=image)
        texts = response.text_annotations
        
        if response.error.message:
            raise RuntimeError(f"Google Vision API Error: {response.error.message}")
            
        if texts:
            logger.info("Google Cloud Vision OCR extraction complete.")
            return texts[0].description
        return ""

    def tesseract_ocr(self, image_bytes: bytes) -> str:
        """Extracts text from images using pytesseract (Tesseract OCR)."""
        logger.info("Running Tesseract OCR...")
        try:
            image = Image.open(io.BytesIO(image_bytes))
            text = pytesseract.image_to_string(image)
            logger.info("Tesseract OCR extraction complete.")
            return text
        except pytesseract.TesseractNotFoundError:
            logger.warning("Tesseract binary not found on local path.")
            raise RuntimeError("Tesseract OCR engine is not installed on the system.")
        except Exception as e:
            logger.error(f"Tesseract OCR failed: {e}")
            raise e

    async def perform_ocr(self, file_bytes: bytes, filename: str, content_type: str) -> str:
        """Coordinates text extraction and OCR pipelines using helper methods."""
        pdf_text = self._try_pdf_direct_parsing(file_bytes, filename, content_type)
        if pdf_text:
            return pdf_text

        vision_text = await self._try_google_vision_ocr(file_bytes)
        if vision_text:
            return vision_text

        tess_text = self._try_tesseract_ocr(file_bytes)
        if tess_text:
            return tess_text

        return await self._try_gemini_fallback_ocr(file_bytes, filename, content_type)

    def _try_pdf_direct_parsing(self, file_bytes: bytes, filename: str, content_type: str) -> str:
        """Helper to run direct PDF extraction if format matches."""
        if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
            pdf_text = self.extract_text_from_pdf(file_bytes)
            if pdf_text.strip():
                return pdf_text
        return ""

    async def _try_google_vision_ocr(self, file_bytes: bytes) -> str:
        """Helper to execute Google Vision OCR and catch any failures."""
        if self.has_vision_creds:
            try:
                vision_text = await self.google_vision_ocr(file_bytes)
                if vision_text.strip():
                    return vision_text
            except Exception as e:
                logger.warning(f"Google Vision OCR failed: {e}. Trying Tesseract fallback...")
        return ""

    def _try_tesseract_ocr(self, file_bytes: bytes) -> str:
        """Helper to execute Tesseract OCR and catch any failures."""
        try:
            tess_text = self.tesseract_ocr(file_bytes)
            if tess_text.strip():
                return tess_text
        except Exception as e:
            logger.warning(f"Tesseract OCR failed: {e}. Falling back to Gemini Multimodal.")
        return ""

    async def _try_gemini_fallback_ocr(self, file_bytes: bytes, filename: str, content_type: str) -> str:
        """Final OCR fallback helper using Gemini Multimodal vision parsing."""
        logger.info("Invoking Gemini multimodal API as final OCR fallback...")
        try:
            gemini_svc = GeminiAIService()
            prompt = (
                "Please read this utility bill carefully. Transcribe all text, numbers, "
                "tables, and figures you see on it. Return only the transcript."
            )
            mime_type = content_type
            if content_type == "application/pdf":
                if gemini_svc.is_mock:
                    return (
                        "MOCK PDF UTILITY BILL TEXT\nAccount: 12345-6789\n"
                        "Billing period: 2026-05\nConsumption: 420.0 kWh\nTotal charges: $64.50"
                    )
            
            transcription = await gemini_svc.analyze_multimodal(
                image_bytes=file_bytes, mime_type=mime_type, prompt=prompt
            )
            logger.info("Gemini Multimodal OCR fallback complete.")
            return transcription
        except Exception as gemini_err:
            logger.error(f"All OCR pipelines (including Gemini) failed: {gemini_err}")
            return (
                "DEMO BILL OCR TEXT (FALLBACK)\nMonthly Electricity Invoice\n"
                "Billing Period: 2026-05\nTotal Usage: 350.0 kWh\nTotal Cost: $55.00"
            )
