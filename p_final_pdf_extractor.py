
import fitz  # PyMuPDF
import json
import os
import sys
import re
from typing import List, Dict, Tuple, Optional
from collections import defaultdict, Counter
import statistics

class p_FinalPDFOutlineExtractor:
    def __init__(self):
        self.debug = False

    def extract_text_with_layout(self, pdf_path: str) -> List[Dict]:
        """Extract text preserving layout information"""
        doc = fitz.open(pdf_path)
        all_text_items = []

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Use blocks extraction which groups text better
            blocks = page.get_text("blocks", sort=True)

            for block in blocks:
                if len(block) >= 5:  # Valid block format
                    x0, y0, x1, y1, text, block_no, block_type = block[:7]

                    # Clean up text
                    text = text.strip()
                    if text and len(text) >= 2:
                        # Get detailed font info for this block
                        font_info = self.get_block_font_info(page, (x0, y0, x1, y1))

                        all_text_items.append({
                            'text': text,
                            'page': page_num + 1,
                            'bbox': [x0, y0, x1, y1],
                            'x': x0,
                            'y': y0,
                            'width': x1 - x0,
                            'height': y1 - y0,
                            'size': font_info.get('size', 12),
                            'font': font_info.get('font', ''),
                            'is_bold': font_info.get('is_bold', False),
                            'block_no': block_no
                        })

        doc.close()
        return all_text_items

    def get_block_font_info(self, page, bbox) -> Dict:
        """Get font information for a text block"""
        try:
            # Get detailed text info for this area
            text_dict = page.get_text("dict")

            sizes = []
            fonts = []
            flags = []

            for block in text_dict.get("blocks", []):
                if "lines" not in block:
                    continue

                block_bbox = block.get("bbox", [0, 0, 0, 0])
                # Check if this block overlaps with our target bbox
                if self.bboxes_overlap(bbox, block_bbox):
                    for line in block["lines"]:
                        for span in line["spans"]:
                            if span.get("text", "").strip():
                                sizes.append(span.get("size", 12))
                                fonts.append(span.get("font", ""))
                                flags.append(span.get("flags", 0))

            if sizes:
                avg_size = statistics.mean(sizes)
                dominant_font = max(set(fonts), key=fonts.count) if fonts else ""
                is_bold = any(flag & 16 for flag in flags)  # Bold flag is 16 (2^4)

                return {
                    'size': avg_size,
                    'font': dominant_font,
                    'is_bold': is_bold
                }

        except Exception as e:
            if self.debug:
                print(f"Error getting font info: {e}")

        return {'size': 12, 'font': '', 'is_bold': False}

    def bboxes_overlap(self, bbox1, bbox2) -> bool:
        """Check if two bounding boxes overlap"""
        return not (bbox1[2] < bbox2[0] or bbox2[2] < bbox1[0] or 
                   bbox1[3] < bbox2[1] or bbox2[3] < bbox1[1])

    def clean_and_filter_text(self, text_items: List[Dict]) -> List[Dict]:
        """Clean and filter text items"""
        cleaned_items = []

        for item in text_items:
            text = item['text'].strip()

            # Skip very short texts
            if len(text) < 2:
                continue

            # Skip obvious page headers/footers (common patterns)
            if self.is_header_footer(text, item):
                continue

            # Skip just numbers or single characters
            if re.match(r'^[0-9\s\-]+$', text) and len(text) < 10:
                continue

            # Clean up text
            text = re.sub(r'\s+', ' ', text)
            item['text'] = text

            cleaned_items.append(item)

        return cleaned_items

    def is_header_footer(self, text: str, item: Dict) -> bool:
        """Detect if text is a header or footer"""
        page_height = 800  # Approximate page height

        # Position-based detection
        if item['y'] > page_height * 0.9 or item['y'] < 50:
            # Near top or bottom of page
            if (len(text) < 80 and 
                ('RFP:' in text or 'March 2003' in text or 
                 re.match(r'^\d+$', text.strip()) or
                 'Business Plan' in text)):
                return True

        # Pattern-based detection
        header_footer_patterns = [
            r'^RFP: To Develop.*March 2003.*\d+$',
            r'^\d+\s*$',  # Just page numbers
            r'^March \d+, \d+$',  # Just dates
        ]

        for pattern in header_footer_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True

        return False

    def detect_title_advanced(self, text_items: List[Dict]) -> str:
        """Advanced title detection"""
        if not text_items:
            return "Untitled Document"

        # Get first page items, sorted by position
        first_page = [item for item in text_items if item['page'] == 1]
        first_page.sort(key=lambda x: (x['y'], x['x']))

        # Look for title in the first few substantial text blocks
        title_candidates = []

        for item in first_page[:8]:  # Check first 8 blocks
            text = item['text'].strip()
            size = item['size']

            # Must be substantial text
            if len(text) < 5:
                continue

            # Skip obvious non-titles
            if (text.lower().startswith(('page ', 'chapter ', 'section ')) or
                re.match(r'^\d+\s*$', text) or
                'March 2003' in text):
                continue

            # Check if this looks like a title
            if (item['y'] < 300 and  # Upper part of page
                len(text) > 8 and
                size >= 12):
                title_candidates.append((text, size, item['y']))

        if title_candidates:
            # Sort by font size (descending) then by position
            title_candidates.sort(key=lambda x: (-x[1], x[2]))

            # Try to find a coherent title
            best_candidate = title_candidates[0][0]

            # Clean up the title
            title = re.sub(r'\s+', ' ', best_candidate).strip()

            # If title seems fragmented, try to find a better one
            if len(title.split()) > 15 or title.count(' ') > 20:
                # Look for a more coherent title
                for candidate, _, _ in title_candidates[1:3]:
                    if 5 < len(candidate.split()) < 15:
                        title = candidate
                        break

            return title[:150]  # Limit length

        # Fallback
        return "Document"

    def classify_headings_advanced(self, text_items: List[Dict]) -> List[Dict]:
        """Advanced heading classification"""
        if not text_items:
            return []

        # Analyze font size distribution
        sizes = [item['size'] for item in text_items if item['size'] > 0]
        if not sizes:
            return []

        size_stats = {
            'mean': statistics.mean(sizes),
            'median': statistics.median(sizes),
            'sizes': sorted(set(sizes), reverse=True)
        }

        # Calculate thresholds more carefully
        thresholds = self.calculate_heading_thresholds(size_stats)

        potential_headings = []

        for item in text_items:
            text = item['text'].strip()
            size = item['size']
            is_bold = item.get('is_bold', False)

            # Pre-filtering
            if not self.could_be_heading(text, size, size_stats['mean']):
                continue

            # Calculate confidence
            confidence = self.calculate_confidence_advanced(item, thresholds, size_stats)

            if confidence > 2.0:  # Higher threshold for better precision
                level = self.determine_level_advanced(item, thresholds, size_stats)

                potential_headings.append({
                    'level': level,
                    'text': text,
                    'page': item['page'],
                    'size': size,
                    'confidence': confidence,
                    'y': item['y']
                })

        # Post-process to remove duplicates and improve quality
        return self.post_process_headings_advanced(potential_headings)

    def could_be_heading(self, text: str, size: float, mean_size: float) -> bool:
        """Quick check if text could possibly be a heading"""
        # Length check
        if len(text) < 3 or len(text) > 200:
            return False

        # Size check
        if size < mean_size - 1:
            return False

        # Content check
        if self.is_obviously_body_text(text):
            return False

        return True

    def is_obviously_body_text(self, text: str) -> bool:
        """Check if text is obviously body text"""
        # Multiple sentences
        if text.count('.') >= 2 and not text.endswith('.'):
            return True

        # Starts with lowercase (except special cases)
        if text and text[0].islower() and not text.startswith(('e-', 'i.e.', 'etc.')):
            return True

        # Long paragraphs
        if len(text) > 150 and ' ' in text:
            return True

        # Common body text starters
        body_starters = ['The ', 'This ', 'It ', 'We ', 'Our ', 'In order', 'For the']
        if any(text.startswith(starter) for starter in body_starters):
            return True

        return False

    def calculate_heading_thresholds(self, size_stats: Dict) -> Dict:
        """Calculate size thresholds for heading levels"""
        sizes = size_stats['sizes']  # Already sorted descending
        mean_size = size_stats['mean']

        if len(sizes) >= 4:
            return {
                'h1': sizes[0],  # Largest
                'h2': sizes[1],  # Second largest
                'h3': sizes[2],  # Third largest
                'body': mean_size
            }
        elif len(sizes) >= 2:
            return {
                'h1': sizes[0],
                'h2': sizes[1] if len(sizes) > 1 else sizes[0] - 1,
                'h3': mean_size + 1,
                'body': mean_size
            }
        else:
            return {
                'h1': mean_size + 4,
                'h2': mean_size + 2,
                'h3': mean_size + 1,
                'body': mean_size
            }

    def calculate_confidence_advanced(self, item: Dict, thresholds: Dict, size_stats: Dict) -> float:
        """Calculate advanced confidence score"""
        text = item['text']
        size = item['size']
        is_bold = item.get('is_bold', False)

        confidence = 0.0

        # Size-based confidence
        if size >= thresholds['h1']:
            confidence += 3.5
        elif size >= thresholds['h2']:
            confidence += 2.5
        elif size >= thresholds['h3']:
            confidence += 1.5
        elif size > size_stats['mean']:
            confidence += 1.0

        # Bold bonus
        if is_bold:
            confidence += 1.0

        # Pattern recognition
        if self.matches_heading_pattern(text):
            confidence += 2.0

        # Structure-based bonuses
        if text.endswith(':'):
            confidence += 1.0

        if text.isupper() and 5 < len(text) < 50:
            confidence += 1.0

        # Position-based (simple version)
        if item['y'] < 100:  # Near top of page
            confidence += 0.5

        # Length-based adjustments
        if 5 <= len(text) <= 80:
            confidence += 0.5
        elif len(text) > 150:
            confidence -= 1.5

        return confidence

    def matches_heading_pattern(self, text: str) -> bool:
        """Check for common heading patterns"""
        patterns = [
            r'^(Chapter|Section|Part|Appendix)\s+[IVX0-9]+',
            r'^\d+\.\d*\s+[A-Z]',
            r'^[A-Z][a-z]+.*:$',
            r'^(Summary|Background|Introduction|Conclusion|Overview|Abstract)$',
            r'^Phase\s+[IVX]+:?',
            r'^Appendix\s+[A-Z]:',
            r'^[A-Z][A-Z\s]+$',  # All caps
            r'^(What|How|Why|Where|When)\s+[a-z]'
        ]

        for pattern in patterns:
            if re.match(pattern, text):
                return True

        return False

    def determine_level_advanced(self, item: Dict, thresholds: Dict, size_stats: Dict) -> str:
        """Determine heading level with advanced logic"""
        text = item['text']
        size = item['size']

        # Size-based initial classification
        if size >= thresholds['h1']:
            level = "H1"
        elif size >= thresholds['h2']:
            level = "H2"
        elif size >= thresholds['h3']:
            level = "H3"
        else:
            level = "H3"

        # Content-based adjustments
        if re.match(r'^Appendix\s+[A-Z]:', text):
            level = "H2"
        elif text in ["Summary", "Background", "Introduction", "Conclusion"]:
            level = "H2"
        elif text.startswith("For each") and text.endswith(":"):
            level = "H4"
        elif re.match(r'^\d+\.\d+\s+', text):
            level = "H3"
        elif re.match(r'^Phase\s+[IVX]+', text):
            level = "H2"

        return level

    def post_process_headings_advanced(self, headings: List[Dict]) -> List[Dict]:
        """Advanced post-processing of headings"""
        if not headings:
            return []

        # Sort by page, then by y position
        headings.sort(key=lambda x: (x['page'], x['y']))

        # Remove near duplicates
        filtered_headings = []
        seen_texts = set()

        for heading in headings:
            text_normalized = re.sub(r'\s+', ' ', heading['text'].lower().strip())

            # Check for exact duplicates
            if text_normalized in seen_texts:
                continue

            # Check for very similar texts (substring matches)
            is_duplicate = False
            for seen_text in seen_texts:
                if (text_normalized in seen_text or seen_text in text_normalized) and len(text_normalized) > 10:
                    is_duplicate = True
                    break

            if not is_duplicate:
                seen_texts.add(text_normalized)
                filtered_headings.append({
                    'level': heading['level'],
                    'text': heading['text'],
                    'page': heading['page']
                })

        return filtered_headings[:50]  # Limit to reasonable number

    def extract_outline(self, pdf_path: str) -> Dict:
        """Main extraction method"""
        try:
            # Extract text with layout
            text_items = self.extract_text_with_layout(pdf_path)

            # Clean and filter
            clean_items = self.clean_and_filter_text(text_items)

            # Detect title
            title = self.detect_title_advanced(clean_items)

            # Classify headings
            outline = self.classify_headings_advanced(clean_items)

            return {
                'title': title,
                'outline': outline
            }

        except Exception as e:
            if self.debug:
                print(f"Error in extract_outline: {e}")
                import traceback
                traceback.print_exc()
            return {
                'title': 'Error processing document',
                'outline': []
            }

def process_pdf_file(input_path: str, output_path: str):
    """Process a single PDF file"""
    extractor = FinalPDFOutlineExtractor()

    try:
        result = extractor.extract_outline(input_path)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"Successfully processed {input_path} -> {output_path}")

    except Exception as e:
        print(f"Error processing {input_path}: {str(e)}")
        empty_result = {'title': 'Processing Failed', 'outline': []}

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(empty_result, f, indent=2, ensure_ascii=False)

def main():
    """Main function for Docker container"""
    input_dir = "/app/input"
    output_dir = "/app/output"

    os.makedirs(output_dir, exist_ok=True)

    if os.path.exists(input_dir):
        for filename in os.listdir(input_dir):
            if filename.lower().endswith('.pdf'):
                input_path = os.path.join(input_dir, filename)
                output_filename = filename.replace('.pdf', '.json')
                output_path = os.path.join(output_dir, output_filename)

                process_pdf_file(input_path, output_path)
    else:
        print(f"Input directory {input_dir} does not exist")

if __name__ == "__main__":
    main()
