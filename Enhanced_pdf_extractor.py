
import fitz  # PyMuPDF
import re
import json
import statistics
import os
import argparse
from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Optional

class EnhancedPDFOutlineExtractor:
   

    def __init__(self):
        """
        Enhanced PDF outline extractor optimized for complex fonts and form documents.
        Focuses on accurate title detection and avoiding false heading classification.
        """
        # Very strict heading patterns - only the most obvious structural indicators
        self.heading_patterns = {
            # Only strong numbered sections with content words
            'h1_definite': re.compile(r'^\s*(\d+)\.\s+([A-Z][a-z].*?[a-z])\s*$', re.IGNORECASE),
            'h2_definite': re.compile(r'^\s*(\d+)\.(\d+)\s+([A-Z][a-z].*?[a-z])\s*$', re.IGNORECASE),

            # Special sections that are definitely H1 (must be standalone)
            'h1_special': re.compile(r'^\s*(Table of Contents|References|Bibliography|Acknowledgements?|Abstract|Summary|Introduction|Conclusion|Appendix [A-Z])\s*$', re.IGNORECASE),
        }

        # Document type detection patterns
        self.document_type_indicators = {
            'form': ['application', 'form', 'for:', 'date:', 'name:', 'address:', 'rsvp:', 'signature'],
            'invitation': ['invited', 'party', 'celebration', 'event', 'rsvp', 'please join'],
            'flyer': ['sale', 'discount', 'special offer', 'limited time', 'call now'],
            'certificate': ['certificate', 'certifies', 'completion', 'achievement'],
        }

        # Text that should NEVER be considered headings
        self.never_headings = [
            'www.', 'http', '.com', '.org', 'email', '@', 
            'copyright', '©', 'page', 'version', 'date:',
            'rsvp:', 'address:', 'phone:', 'contact:',
            '___', '---', '...', 'signature', 'print name'
        ]

    def detect_document_type(self, blocks: List[Dict]) -> str:
        """Detect the type of document to adjust processing strategy."""
        all_text = ' '.join([block['text'].lower() for block in blocks])

        # Count indicators for each document type
        type_scores = {}
        for doc_type, indicators in self.document_type_indicators.items():
            score = sum(1 for indicator in indicators if indicator in all_text)
            type_scores[doc_type] = score

        # Determine document characteristics
        total_blocks = len(blocks)
        avg_text_length = sum(len(block['text']) for block in blocks) / max(total_blocks, 1)

        # Simple heuristics for document type
        if total_blocks < 20 and avg_text_length < 50:
            if type_scores.get('form', 0) > 2:
                return 'form'
            elif type_scores.get('invitation', 0) > 1:
                return 'invitation'
            elif type_scores.get('flyer', 0) > 1:
                return 'flyer'
            else:
                return 'simple'
        elif total_blocks > 100:
            return 'complex_document'
        else:
            return 'standard_document'

    def extract_text_blocks(self, pdf_path: str) -> List[Dict]:
        """Extract text blocks with enhanced font information."""
        doc = fitz.open(pdf_path)
        text_blocks = []

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Try multiple extraction methods for better accuracy
            try:
                # Method 1: Detailed text extraction with font info
                text_dict = page.get_text("dict")
                for block in text_dict["blocks"]:
                    if "lines" in block:
                        for line in block["lines"]:
                            line_text = ""
                            font_sizes = []
                            is_bold = False

                            for span in line["spans"]:
                                line_text += span["text"]
                                font_sizes.append(span.get("size", 12))
                                # Check if text is bold (flags & 16 means bold)
                                if span.get("flags", 0) & 16:
                                    is_bold = True

                            if line_text.strip():
                                avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 12

                                text_blocks.append({
                                    'text': line_text.strip(),
                                    'page': page_num + 1,
                                    'bbox': line["bbox"],
                                    'font_info': {
                                        'size': avg_font_size,
                                        'is_bold': is_bold,
                                        'flags': 16 if is_bold else 0
                                    },
                                    'position': {
                                        'x': line["bbox"][0],
                                        'y': line["bbox"][1],
                                        'width': line["bbox"][2] - line["bbox"][0],
                                        'height': line["bbox"][3] - line["bbox"][1]
                                    }
                                })
            except:
                # Fallback: Simple block extraction
                blocks = page.get_text("blocks")
                for block in blocks:
                    if len(block) >= 6 and block[4]:
                        text = block[4].strip()
                        if text:
                            text_blocks.append({
                                'text': text,
                                'page': page_num + 1,
                                'bbox': block[:4],
                                'font_info': {'size': 12, 'is_bold': False, 'flags': 0},
                                'position': {
                                    'x': block[0],
                                    'y': block[1],
                                    'width': block[2] - block[0],
                                    'height': block[3] - block[1]
                                }
                            })

        doc.close()
        return text_blocks

    def extract_title_enhanced(self, blocks: List[Dict], doc_type: str) -> str:
        """Enhanced title extraction based on document type and visual hierarchy."""
        if not blocks:
            return "Document Title"

        # Strategy varies by document type
        if doc_type in ['invitation', 'flyer', 'form']:
            return self._extract_title_from_visual_document(blocks)
        elif doc_type in ['complex_document', 'standard_document']:
            return self._extract_title_from_structured_document(blocks)
        else:
            return self._extract_title_from_simple_document(blocks)

    def _extract_title_from_visual_document(self, blocks: List[Dict]) -> str:
        """Extract title from visually-designed documents like invitations."""
        # Look for largest font size in first few blocks
        first_page_blocks = [b for b in blocks if b['page'] == 1][:10]

        # Find the block with largest font size that looks like a title
        best_candidate = None
        best_score = 0

        for block in first_page_blocks:
            text = block['text'].strip()
            font_size = block['font_info']['size']
            is_bold = block['font_info']['is_bold']

            # Skip obvious non-titles
            if (len(text) < 3 or 
                any(indicator in text.lower() for indicator in self.never_headings) or
                text.lower().startswith(('page', 'copyright', '©'))):
                continue

            # Score based on visual characteristics
            score = 0
            if font_size > 14:  # Larger font
                score += font_size / 4
            if is_bold:  # Bold text
                score += 10
            if len(text) > 5 and len(text) < 80:  # Reasonable title length
                score += 5
            if text.isupper():  # All caps
                score += 8
            if not any(char in text for char in '.,!?'):  # No punctuation
                score += 3
            if block['position']['y'] < 200:  # Top of page
                score += 5

            if score > best_score:
                best_score = score
                best_candidate = text

        if best_candidate:
            return best_candidate

        # Fallback: first meaningful text
        for block in first_page_blocks:
            text = block['text'].strip()
            if (len(text) > 3 and 
                not any(indicator in text.lower() for indicator in self.never_headings)):
                return text

        return "Document Title"

    def _extract_title_from_structured_document(self, blocks: List[Dict]) -> str:
        """Extract title from structured documents."""
        first_page_blocks = [b for b in blocks if b['page'] == 1]

        for block in first_page_blocks[:5]:
            text = block['text'].strip()
            if (len(text) > 10 and len(text) < 150 and 
                not self._is_navigation_text(text) and
                not text.lower().startswith(('page', 'copyright', '©'))):
                return text

        return "Document Title"

    def _extract_title_from_simple_document(self, blocks: List[Dict]) -> str:
        """Extract title from simple documents."""
        for block in blocks[:5]:
            text = block['text'].strip()
            if len(text) > 5 and len(text) < 100:
                return text
        return "Document Title"

    def should_extract_headings(self, doc_type: str, blocks: List[Dict]) -> bool:
        """Determine if we should attempt to extract headings from this document type."""
        # Don't extract headings from forms, invitations, flyers, etc.
        if doc_type in ['form', 'invitation', 'flyer', 'certificate']:
            return False

        # Don't extract headings from very simple documents
        if len(blocks) < 15:
            return False

        # Check if document has any clear structural indicators
        has_numbered_sections = any(
            self.heading_patterns['h1_definite'].match(block['text']) or 
            self.heading_patterns['h2_definite'].match(block['text'])
            for block in blocks
        )

        has_special_sections = any(
            self.heading_patterns['h1_special'].match(block['text'])
            for block in blocks
        )

        return has_numbered_sections or has_special_sections

    def calculate_ultra_conservative_heading_score(self, block: Dict, doc_type: str) -> Tuple[str, float]:
        """Ultra-conservative heading detection - only obvious structural elements."""
        text = block['text'].strip()

        # Immediate disqualifiers
        if (len(text) < 4 or len(text) > 100 or
            any(never in text.lower() for never in self.never_headings) or
            '___' in text or '---' in text or '...' in text):
            return 'CONTENT', 0.0

        # Only definitive patterns get high scores
        scores = {'H1': 0, 'H2': 0, 'CONTENT': 10}

        # Pattern-based scoring (VERY HIGH REQUIREMENTS)
        if self.heading_patterns['h1_definite'].match(text):
            scores['H1'] = 100  # Definitive
        elif self.heading_patterns['h2_definite'].match(text):
            scores['H2'] = 100  # Definitive
        elif self.heading_patterns['h1_special'].match(text):
            scores['H1'] = 90   # Very strong
        else:
            # No other patterns qualify as headings in ultra-conservative mode
            pass

        # Find highest score with minimum threshold
        if scores['H1'] >= 80:
            return 'H1', min(scores['H1'] / 100.0, 1.0)
        elif scores['H2'] >= 80:
            return 'H2', min(scores['H2'] / 100.0, 1.0)
        else:
            return 'CONTENT', 0.0

    def _is_navigation_text(self, text: str) -> bool:
        """Enhanced navigation text detection."""
        text_lower = text.lower()
        nav_indicators = [
            'page ', 'copyright', '©', 'www.', 'http', '@',
            '.com', '.org', 'version', 'date:', 'revised',
            'rsvp:', 'phone:', 'address:', 'email:'
        ]
        return any(indicator in text_lower for indicator in nav_indicators)

    def extract_outline(self, pdf_path: str) -> Dict:
        """
        Main extraction method with enhanced document type handling.
        """
        # Extract text blocks
        blocks = self.extract_text_blocks(pdf_path)

        if not blocks:
            return {"title": "Empty Document", "outline": []}

        # Detect document type
        doc_type = self.detect_document_type(blocks)

        # Extract title using enhanced method
        title = self.extract_title_enhanced(blocks, doc_type)

        # Decide whether to extract headings based on document type
        if not self.should_extract_headings(doc_type, blocks):
            return {
                'title': title,
                'outline': []  # No headings for forms/invitations/simple docs
            }

        # Process blocks for heading detection (only for appropriate document types)
        potential_headings = []

        for block in blocks:
            text = block['text'].strip()

            # Ultra-conservative heading detection
            level, confidence = self.calculate_ultra_conservative_heading_score(block, doc_type)

            if level != 'CONTENT' and confidence >= 0.8:  # Very high threshold
                potential_headings.append({
                    'level': level,
                    'text': text,
                    'page': block['page'],
                    'confidence': confidence
                })

        # Sort by page and remove duplicates
        potential_headings.sort(key=lambda x: (x['page'], x['text']))
        final_headings = []

        for heading in potential_headings:
            # Avoid duplicates
            if not any(h['text'] == heading['text'] for h in final_headings):
                final_headings.append(heading)

        # Format output
        outline = []
        for heading in final_headings:
            outline.append({
                'level': heading['level'],
                'text': heading['text'],
                'page': heading['page']
            })

        return {
            'title': title,
            'outline': outline
        }

# Main processing function
def process_all_pdfs(input_dir: str = '/app/input', output_dir: str = '/app/output'):
    """Process all PDF files with the enhanced extractor."""
    import os

    extractor = EnhancedPDFOutlineExtractor()

    for filename in os.listdir(input_dir):
        if filename.lower().endswith('.pdf'):
            input_path = os.path.join(input_dir, filename)
            output_filename = filename.replace('.pdf', '.json')
            output_path = os.path.join(output_dir, output_filename)

            try:
                result = extractor.extract_outline(input_path)

                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)

                print(f"Processed: {filename} -> {output_filename}")
                print(f"  Title: {result['title']}")
                print(f"  Headings: {len(result['outline'])}")

            except Exception as e:
                print(f"Error processing {filename}: {e}")




def pprocess_all_pdfs(input_dir="input", output_dir="output"):
    if not os.path.exists(input_dir):
        os.makedirs(input_dir)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for filename in os.listdir(input_dir):
        if filename.lower().endswith('.pdf'):
            pdf_path = os.path.join(input_dir, filename)
            json_path = os.path.join(output_dir, filename.replace('.pdf', '.json'))
            # Extract and save outline here


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='input', help='Input directory with PDFs')
    parser.add_argument('--output', default='output', help='Output directory for JSONs')
    args = parser.parse_args()
    process_all_pdfs(args.input, args.output)




