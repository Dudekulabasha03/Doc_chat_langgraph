import os
import hashlib
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import List
import pypdfium2 as pdfium
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import PdfFormatOption
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain.schema import Document
from config import constants
from config.settings import settings
from utils.logging import logger
import time

class DocumentProcessor:
    def __init__(self):
        self.headers = [("#", "Header 1"), ("##", "Header 2")]
        self.cache_dir = Path(settings.CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def validate_files(self, files: List) -> None:
        """Validate the total size of the uploaded files."""
        total_size = sum(os.path.getsize(f.name) for f in files)
        if total_size > constants.MAX_TOTAL_SIZE:
            raise ValueError(f"Total size exceeds {constants.MAX_TOTAL_SIZE//1024//1024}MB limit")

    def process(self, files: List) -> List:
        """Process files with caching for subsequent queries"""
        self.validate_files(files)
        all_chunks = []
        seen_hashes = set()
        
        for file in files:
            try:
                # Generate content-based hash for caching
                with open(file.name, "rb") as f:
                    file_hash = self._generate_hash(f.read())
                
                cache_path = self.cache_dir / f"{file_hash}.pkl"
                
                if self._is_cache_valid(cache_path):
                    logger.info(f"Loading from cache: {file.name}")
                    chunks = self._load_from_cache(cache_path)
                else:
                    logger.info(f"Processing and caching: {file.name}")
                    chunks = self._process_file(file)
                    self._save_to_cache(chunks, cache_path)
                
                # Deduplicate chunks across files
                for chunk in chunks:
                    chunk_hash = self._generate_hash(chunk.page_content.encode())
                    if chunk_hash not in seen_hashes:
                        all_chunks.append(chunk)
                        seen_hashes.add(chunk_hash)
                        
            except Exception as e:
                logger.error(f"Failed to process {file.name}: {str(e)}")
                continue
                
        logger.info(f"Total unique chunks: {len(all_chunks)}")
        return all_chunks

    def _process_file(self, file) -> List:
        """Process file with multiple fallback strategies"""
        if not file.name.endswith(('.pdf', '.docx', '.txt', '.md')):
            logger.warning(f"Skipping unsupported file type: {file.name}")
            return []

        file_extension = Path(file.name).suffix.lower()
        
        # Handle text and markdown files directly
        if file_extension in ['.txt', '.md']:
            return self._process_text_file(file)
        
        # Handle PDF files with fallback strategies
        elif file_extension == '.pdf':
            return self._process_pdf_with_fallback(file)
        
        # Handle DOCX and other files with docling (if available)
        else:
            return self._process_with_docling(file)
    
    def _process_text_file(self, file) -> List:
        """Process text/markdown files directly"""
        try:
            with open(file.name, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create a document object
            doc = Document(page_content=content)
            
            # Split using markdown splitter for structured content
            if file.name.endswith('.md'):
                splitter = MarkdownHeaderTextSplitter(self.headers)
                return splitter.split_text(content)
            else:
                # Use recursive character splitter for plain text
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=200
                )
                return splitter.split_documents([doc])
                
        except Exception as e:
            logger.error(f"Failed to process text file {file.name}: {str(e)}")
            return []
    
    def _process_pdf_with_fallback(self, file) -> List:
        """Process PDF with multiple fallback strategies"""
        
        # Strategy 1: Try pypdfium2 (fast, simple text extraction)
        try:
            logger.info(f"Trying pypdfium2 for {file.name}")
            return self._extract_with_pypdfium(file)
        except Exception as e:
            logger.warning(f"pypdfium2 failed for {file.name}: {str(e)}")
        
        # Strategy 2: Try docling with simplified configuration
        try:
            logger.info(f"Trying simplified docling for {file.name}")
            return self._extract_with_simple_docling(file)
        except Exception as e:
            logger.warning(f"Simplified docling failed for {file.name}: {str(e)}")
        
        # Strategy 3: Try docling with full configuration (with timeout)
        try:
            logger.info(f"Trying full docling with timeout for {file.name}")
            return self._extract_with_timeout_docling(file)
        except Exception as e:
            logger.error(f"All PDF processing methods failed for {file.name}: {str(e)}")
            return []
    
    def _extract_with_pypdfium(self, file) -> List:
        """Extract text using pypdfium2 (simple and fast)"""
        pdf = pdfium.PdfDocument(file.name)
        
        all_text = []
        for page_num in range(len(pdf)):
            page = pdf.get_page(page_num)
            textpage = page.get_textpage()
            text = textpage.get_text_range()
            if text.strip():  # Only add non-empty pages
                all_text.append(f"## Page {page_num + 1}\n\n{text}")
        
        # Combine all pages
        full_content = "\n\n".join(all_text)
        
        # Split using markdown splitter
        splitter = MarkdownHeaderTextSplitter(self.headers)
        chunks = splitter.split_text(full_content)
        
        # If no chunks from markdown splitter, use recursive splitter
        if not chunks:
            doc = Document(page_content=full_content)
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            chunks = splitter.split_documents([doc])
        
        return chunks
    
    def _extract_with_simple_docling(self, file) -> List:
        """Extract using docling with minimal configuration"""
        # Create pipeline options that avoid downloading large models
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False  # Disable OCR to avoid model downloads
        pipeline_options.do_table_structure = False  # Disable table structure detection
        
        # Configure format options
        format_options = {
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
        
        converter = DocumentConverter(format_options=format_options)
        result = converter.convert(file.name)
        markdown = result.document.export_to_markdown()
        
        splitter = MarkdownHeaderTextSplitter(self.headers)
        return splitter.split_text(markdown)
    
    def _extract_with_timeout_docling(self, file) -> List:
        """Extract using full docling with timeout"""
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Docling processing timed out")
        
        # Set timeout to 60 seconds
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(60)
        
        try:
            converter = DocumentConverter()
            result = converter.convert(file.name)
            markdown = result.document.export_to_markdown()
            
            splitter = MarkdownHeaderTextSplitter(self.headers)
            return splitter.split_text(markdown)
        finally:
            signal.alarm(0)  # Cancel the alarm
    
    def _process_with_docling(self, file) -> List:
        """Process other file types with docling"""
        try:
            converter = DocumentConverter()
            result = converter.convert(file.name)
            markdown = result.document.export_to_markdown()
            
            splitter = MarkdownHeaderTextSplitter(self.headers)
            return splitter.split_text(markdown)
        except Exception as e:
            logger.error(f"Docling processing failed for {file.name}: {str(e)}")
            return []

    def _generate_hash(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def _save_to_cache(self, chunks: List, cache_path: Path):
        with open(cache_path, "wb") as f:
            pickle.dump({
                "timestamp": datetime.now().timestamp(),
                "chunks": chunks
            }, f)

    def _load_from_cache(self, cache_path: Path) -> List:
        with open(cache_path, "rb") as f:
            data = pickle.load(f)
        return data["chunks"]

    def _is_cache_valid(self, cache_path: Path) -> bool:
        if not cache_path.exists():
            return False
            
        cache_age = datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)
        return cache_age < timedelta(days=settings.CACHE_EXPIRE_DAYS)