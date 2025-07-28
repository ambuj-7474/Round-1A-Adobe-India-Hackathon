#!/usr/bin/env python3
"""
PDF Outline Extractor

This script extracts structured outlines from PDF files, identifying the document title
and headings (H1, H2, H3) along with their page numbers.

The output is a JSON file with the following structure:
{
    "title": "Document Title",
    "outline": [
        {"text": "Heading 1", "level": "H1", "page": 1},
        {"text": "Heading 2", "level": "H2", "page": 2},
        ...
    ]
}
"""

import os
import re
import sys
import json
import logging
import unicodedata
from time import time
from pathlib import Path

import fitz  # PyMuPDF
from tqdm import tqdm
import codecs  # For handling encoding issues

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Performance tracking
class PerformanceTracker:
    """Track processing time for performance optimization."""
    
    def __init__(self):
        self.start_time = time()
        self.checkpoints = {}
        
    def checkpoint(self, name):
        """Record a checkpoint with the given name."""
        self.checkpoints[name] = time() - self.start_time
        
    def get_total_time(self):
        """Get the total elapsed time."""
        return time() - self.start_time
        
    def report(self):
        """Log performance report."""
        logger.info(f"Performance Report:")
        for name, elapsed in sorted(self.checkpoints.items(), key=lambda x: x[1]):
            logger.info(f"  {name}: {elapsed:.4f}s")
        logger.info(f"Total time: {self.get_total_time():.4f}s")


def clean_text(text):
    """Clean and normalize extracted text with multilingual support.
    
    Args:
        text: The text to clean
        
    Returns:
        Cleaned and normalized text with proper handling of various scripts
    """
    if not text:
        return ""
    
    # Handle potential encoding issues with UTF-8 encoding/decoding
    try:
        # Try to ensure we're working with proper Unicode
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='replace')
        elif isinstance(text, str):
            # Ensure we have valid UTF-8
            text = text.encode('utf-8', errors='replace').decode('utf-8')
    except (UnicodeError, AttributeError):
        # If there's any issue, try a different approach
        try:
            # Try with a different encoding that might work better for some PDFs
            if isinstance(text, bytes):
                text = text.decode('utf-8', errors='replace')
            else:
                text = str(text)
        except Exception:
            # Last resort fallback
            text = str(text)
        
    # Apply NFC normalization instead of NFKC for better display of CJK and Indic scripts
    # NFC preserves more distinctions in many scripts while still normalizing
    text = unicodedata.normalize('NFC', text)
    
    # Remove control characters while preserving all script characters
    text = ''.join(ch for ch in text if unicodedata.category(ch)[0] != 'C')
    
    # Normalize whitespace (works across scripts)
    text = re.sub(r'\s+', ' ', text)
    
    # Trim and remove trailing punctuation (universal and script-specific)
    text = text.strip()
    
    # Handle both Latin and non-Latin punctuation
    # Include common CJK punctuation like 。、, Devanagari punctuation like ।, and Arabic punctuation like ،
    text = re.sub(r'[,:;.\-\–\—。、।،؛]+$', '', text)
    
    # Additional normalization for better Unicode handling
    # Normalize CJK punctuation variants
    text = text.replace('\u3000', ' ')  # Ideographic space to regular space
    
    # Fix common encoding issues with CJK and Indic scripts
    text = text.replace('\ufffd', '')  # Remove replacement character
    
    return text


def is_heading(text, font_size, is_bold, avg_font_size):
    """Determine if the given text is likely a heading with multilingual support.
    
    Args:
        text: The text to analyze (in any language/script)
        font_size: The font size of the text
        is_bold: Whether the text is bold
        avg_font_size: The average font size in the document
        
    Returns:
        Boolean indicating if the text is likely a heading
    """
    # Skip empty or very short text (universal)
    if not text or len(text) < 3:
        return False
        
    # Skip very long text (likely paragraphs) - adjusted for different scripts
    # Some languages like Chinese/Japanese use fewer characters to express the same content
    # Calculate text length based on character width category
    # Count wide characters (CJK) as 2, normal as 1
    effective_length = sum(2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1 for c in text)
    if effective_length > 200:
        return False
        
    # Skip text with too many special characters (universal)
    if re.search(r'[~@#$%^&*_+=\\|<>/]{2,}', text):
        return False
    
    # Language-specific patterns for non-headings
    # English
    if re.search(r'(written by|authored by|prepared by|compiled by|edited by)', text.lower()):
        return False
    # Japanese
    if re.search(r'(著者|作成者|編集者)', text):
        return False
    # Hindi
    if re.search(r'(द्वारा लिखित|द्वारा तैयार|द्वारा संकलित)', text):
        return False
        
    # Reject long sentences with punctuation endings (language-agnostic approach)
    # Check for various end punctuation across scripts
    end_punct = r'[.。।?？!！]\s*$'
    if re.search(end_punct, text) and effective_length > 100 and not re.match(r'^\d+(\.\d+)*\.?\s+', text):
        return False
        
    # Check for heading-like formatting (universal and language-specific)
    # 1. Numbered headings (e.g., "1." or "1.1") - works across languages
    if re.match(r'^\d+(\.\d+)*\.?\s+', text):
        return True
        
    # 2. Chapter/section markers in various languages
    chapter_pattern = r'^(chapter|section|part|章|節|भाग|अध्याय|खंड)\s*\d+'
    if re.search(chapter_pattern, text, re.IGNORECASE):
        return True
        
    # 3. Font size significantly larger than average (universal)
    if font_size > avg_font_size * 1.2:
        return True
        
    # 4. Bold text with decent size (universal)
    if is_bold and font_size >= avg_font_size:
        return True
        
    # 5. Script-aware capitalization check
    # For Latin scripts: check for title case
    # For other scripts: rely more on font properties
    has_latin = any(c.isalpha() and unicodedata.name(c, '').startswith('LATIN') for c in text if c.isalpha())
    
    if has_latin:
        words = text.split()
        if len(words) <= 6 and sum(1 for w in words if w and w[0].isupper()) / max(1, len(words)) > 0.5:
            return True
            
        # 6. All caps text for Latin scripts (often used for headings)
        if text.isupper() and len(text) < 50:
            return True
    else:
        # For non-Latin scripts, rely more on formatting and length
        if len(text.split()) <= 10 and font_size >= avg_font_size:
            return True
        
    # Default case - not a heading
    return False


def determine_heading_level(text, font_size, is_bold, font_sizes):
    """Determine the heading level (H1, H2, H3) based on text and formatting with multilingual support.
    
    Args:
        text: The heading text (in any language/script)
        font_size: The font size of the text
        is_bold: Whether the text is bold
        font_sizes: List of all heading font sizes for relative comparison
        
    Returns:
        String indicating heading level ("H1", "H2", or "H3")
    """
    if not font_sizes:
        # Fallback if no font sizes available
        if is_bold and font_size >= 14:
            return "H1"
        elif is_bold or font_size >= 12:
            return "H2"
        else:
            return "H3"
    
    # Sort font sizes in descending order
    sorted_sizes = sorted(font_sizes, reverse=True)
    
    # Special case for document title and main sections in multiple languages
    if re.match(r'^(table of contents|index|appendix|references|bibliography|glossary|abstract|目次|索引|附録|参考文献|用語集|概要|विषय-सूची|अनुक्रमणिका|परिशिष्ट|संदर्भ|शब्दावली|सारांश)$', 
               text.lower()):
        return "H1"
        
    # Check for explicit chapter/section markers in multiple languages
    if re.match(r'^(chapter|section|章|節|अध्याय|खंड)\s*\d+', text, re.IGNORECASE):
        return "H1"
    
    # Determine level based on numbering pattern (universal across languages)
    if re.match(r'^\d+\.\s+', text):
        # Main section (e.g., "1. Introduction")
        return "H1"
    elif re.match(r'^\d+\.\d+', text):
        # Subsection (e.g., "1.1 Background")
        return "H2"
    elif re.match(r'^\d+\.\d+\.\d+', text):
        # Sub-subsection (e.g., "1.1.1 History")
        return "H3"
    
    # Check for special Unicode bullet/numbering used in some languages
    if re.match(r'^[\u2460-\u2473\u3251-\u32bf\u2776-\u277f]', text):  # Circled numbers/special bullets
        # These are often used for major sections in CJK documents
        return "H2"
    
    # Determine level based on font size
    if len(sorted_sizes) >= 3:
        # If we have at least 3 different sizes, use them to determine levels
        if font_size >= sorted_sizes[0] * 0.9:  # Within 90% of largest size
            return "H1"
        elif font_size >= sorted_sizes[len(sorted_sizes)//2] * 0.9:  # Middle range
            return "H2"
        else:
            return "H3"
    else:
        # Simpler heuristic with fewer size samples
        if font_size >= sorted_sizes[0] * 0.9:  # Close to largest size
            return "H1"
        else:
            return "H2" if is_bold else "H3"


def extract_title(doc, headings):
    """Extract the document title with multilingual support.
    
    Args:
        doc: The PyMuPDF document
        headings: List of extracted headings
        
    Returns:
        The document title as a string
    """
    # Try to get title from document metadata
    title = doc.metadata.get("title")
    if title and len(title.strip()) > 3:
        return title.strip()
    
    # If no metadata title, use the first heading if available
    if headings:
        # Sort by page number and font size
        sorted_headings = sorted(headings, key=lambda h: (h["page"], -h["font_size"]))
        
        # Check if the first heading is a reasonable title
        first_heading = sorted_headings[0]["text"]
        # Adjust length check for different scripts
        effective_length = sum(2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1 for c in first_heading)
        if effective_length < 150 and not re.match(r'^\d+\.\s+', first_heading):
            return first_heading
    
    # Fallback to first page text analysis
    page = doc[0]
    blocks = page.get_text("dict")["blocks"]
    
    # Find the largest text on the first page
    largest_text = ""
    largest_size = 0
    
    for block in blocks:
        if "lines" not in block:
            continue
            
        for line in block["lines"]:
            if "spans" not in line:
                continue
                
            for span in line["spans"]:
                text = span["text"].strip()
                # Consider CJK and other non-Latin scripts when evaluating text length
                effective_length = sum(2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1 for c in text)
                if span["size"] > largest_size and effective_length > 3:
                    largest_size = span["size"]
                    largest_text = text
    
    # Check for vertical text patterns (common in Japanese formal documents)
    if not largest_text:
        text_blocks = []
        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                if "spans" not in line:
                    continue
                for span in line["spans"]:
                    if len(span["text"].strip()) > 0:
                        text_blocks.append(span["text"].strip())
        
        # Look for short consecutive lines that might form a vertical title
        if len(text_blocks) >= 3:
            short_blocks = [block for block in text_blocks[:5] if 1 < len(block) < 10]
            if len(short_blocks) >= 3:
                largest_text = ' '.join(short_blocks[:3])
    
    return largest_text if largest_text else "Untitled Document"


def extract_outline(pdf_path, max_pages=100):
    """Extract structured outline from a PDF file with multilingual support.
    
    Args:
        pdf_path: Path to the PDF file (in any language/script)
        max_pages: Maximum number of pages to process
        
    Returns:
        Dictionary with title and outline
    """
    performance = PerformanceTracker()
    
    try:
        # Open the PDF with enhanced language support
        doc = fitz.open(pdf_path)
        performance.checkpoint("Open PDF")
        
        # Limit pages for performance
        num_pages = min(len(doc), max_pages)
        
        # Collect font statistics to determine heading levels
        font_stats = []
        heading_candidates = []
        
        # First pass: collect font statistics and identify potential headings
        logger.info(f"Processing {pdf_path} ({num_pages} pages)")
        
        for page_num in tqdm(range(num_pages), desc="Analyzing pages"):
            page = doc[page_num]
            # Use enhanced text extraction with additional flags for better encoding handling
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_LIGATURES | fitz.TEXT_PRESERVE_WHITESPACE | fitz.TEXT_DEHYPHENATE)["blocks"]
            
            for block in blocks:
                if "lines" not in block:
                    continue
                    
                for line in block["lines"]:
                    if "spans" not in line:
                        continue
                        
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if not text:
                            continue
                            
                        font_size = span["size"]
                        font_stats.append(font_size)
                        
                        # Enhanced check for bold text across different languages
                        flags = span.get("flags", 0)
                        is_bold = (flags & 2) != 0
                        font_name = span.get("font", "")
                        if ("bold" in font_name.lower() or 
                            "heavy" in font_name.lower() or 
                            "black" in font_name.lower() or 
                            "strong" in font_name.lower()):
                            is_bold = True
                        
                        # Store potential heading
                        heading_candidates.append({
                            "text": text,
                            "font_size": font_size,
                            "is_bold": is_bold,
                            "page": page_num + 1  # 1-indexed page numbers
                        })
        
        performance.checkpoint("Collect font statistics")
        
        # Calculate average font size
        avg_font_size = sum(font_stats) / max(1, len(font_stats))
        
        # Second pass: identify actual headings and determine levels
        headings = []
        heading_font_sizes = []
        
        # Group spans into lines for better heading detection
        lines = []
        current_line = {"text": "", "font_size": 0, "is_bold": False, "page": 0}
        
        for candidate in heading_candidates:
            # Enhanced line merging for multilingual text
            if not current_line["text"]:
                current_line = candidate.copy()
            elif candidate["page"] == current_line["page"] and \
                 abs(candidate["font_size"] - current_line["font_size"]) < 1:
                # Merge with current line
                current_line["text"] += " " + candidate["text"]
                current_line["is_bold"] = current_line["is_bold"] or candidate["is_bold"]
            else:
                # Process completed line
                lines.append(current_line)
                current_line = candidate.copy()
        
        # Add the last line
        if current_line["text"]:
            lines.append(current_line)
        
        # Process merged lines with enhanced multilingual support
        for line in lines:
            text = clean_text(line["text"])
            if not text:
                continue
                
            if is_heading(text, line["font_size"], line["is_bold"], avg_font_size):
                heading_font_sizes.append(line["font_size"])
                headings.append({
                    "text": text,
                    "font_size": line["font_size"],
                    "is_bold": line["is_bold"],
                    "page": line["page"]
                })
        
        performance.checkpoint("Identify headings")
        
        # Extract title with multilingual support
        title = extract_title(doc, headings)
        performance.checkpoint("Extract title")
        
        # Determine heading levels with enhanced multilingual support
        outline = []
        for heading in headings:
            level = determine_heading_level(
                heading["text"], 
                heading["font_size"], 
                heading["is_bold"],
                heading_font_sizes
            )
            
            outline.append({
                "text": heading["text"],
                "level": level,
                "page": heading["page"]
            })
        
        performance.checkpoint("Determine heading levels")
        
        # Close the document
        doc.close()
        
        # Create the result with proper Unicode handling
        result = {
            "title": title,
            "outline": outline
        }
        
        performance.checkpoint("Create result")
        performance.report()
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing {pdf_path}: {str(e)}")
        return {"title": "Error", "outline": []}


def process_pdfs(input_dir, output_dir):
    """Process all PDFs in the input directory and save results to the output directory.
    
    Args:
        input_dir: Directory containing PDF files
        output_dir: Directory to save JSON output files
    """
    # Ensure output directory exists and is not inside the input directory
    if os.path.commonpath([os.path.abspath(input_dir)]) == os.path.commonpath([os.path.abspath(input_dir), os.path.abspath(output_dir)]):
        # If output_dir is inside input_dir, use the project root output directory instead
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, "output")
        logger.warning(f"Output directory cannot be inside input directory. Using {output_dir} instead.")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all PDF files
    pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {input_dir}")
        return
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    # Process each PDF
    for pdf_file in pdf_files:
        pdf_path = os.path.join(input_dir, pdf_file)
        output_file = os.path.join(output_dir, pdf_file.replace('.pdf', '.json'))
        
        logger.info(f"Processing {pdf_file}")
        result = extract_outline(pdf_path)
        
        # Save the result with enhanced Unicode handling
        # Apply Unicode normalization to the entire result
        def ensure_unicode(obj):
            if isinstance(obj, dict):
                return {k: ensure_unicode(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [ensure_unicode(item) for item in obj]
            elif isinstance(obj, str):
                # Try to fix any encoding issues
                try:
                    # Normalize to NFC form which is better for display
                    return unicodedata.normalize('NFC', obj)
                except Exception:
                    # If normalization fails, return as is
                    return obj
            else:
                return obj
        
        # Apply Unicode normalization to the entire result
        result = ensure_unicode(result)
        
        # Write with UTF-8 encoding and ensure_ascii=False to preserve Unicode
    # Use codecs for better handling of Unicode characters
    with codecs.open(output_file, 'w', encoding='utf-8') as f:
        # Convert to JSON with proper Unicode handling
        json_str = json.dumps(result, ensure_ascii=False, indent=2)
        # Write directly to avoid any encoding issues
        f.write(json_str)
        
        logger.info(f"Saved outline to {output_file}")


def main():
    """Main entry point."""
    # Default directories for Docker environment
    input_dir = "/app/input"
    output_dir = "/app/output"
    
    # Allow overriding directories for testing
    if len(sys.argv) > 2:
        input_dir = sys.argv[1]
        output_dir = sys.argv[2]
    elif len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        # Single file mode
        pdf_path = sys.argv[1]
        # Always use the output directory at the project root
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        result = extract_outline(pdf_path)
        
        # Apply Unicode normalization to ensure proper multilingual character encoding
        def ensure_unicode(obj):
            if isinstance(obj, dict):
                return {k: ensure_unicode(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [ensure_unicode(item) for item in obj]
            elif isinstance(obj, str):
                # Try to fix any encoding issues
                try:
                    # Normalize to NFC form which is better for display
                    return unicodedata.normalize('NFC', obj)
                except Exception:
                    # If normalization fails, return as is
                    return obj
            else:
                return obj
        
        # Apply Unicode normalization to the entire result
        result = ensure_unicode(result)
        
        # Print the result
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # Save the result to output directory
        output_file = os.path.join(output_dir, os.path.basename(pdf_path).replace('.pdf', '.json'))
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved outline to {output_file} with multilingual support")
        return
    
    # Process all PDFs
    process_pdfs(input_dir, output_dir)


if __name__ == "__main__":
    main()