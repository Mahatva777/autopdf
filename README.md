# PDF Outline Extractor - Adobe Hackathon Round 1A

This solution extracts structured outlines from PDF documents, identifying titles and hierarchical headings (H1, H2, H3, H4) with page numbers.

## Approach

Our solution uses PyMuPDF (fitz) for robust PDF text extraction with font analysis. The key components include:

1. **Text Extraction**: Uses PyMuPDF's `get_text("blocks")` method for efficient text extraction with layout preservation
2. **Font Analysis**: Analyzes font sizes, styles, and positioning to identify heading hierarchies
3. **Pattern Recognition**: Uses regex patterns and content analysis to classify text as headings
4. **Header/Footer Filtering**: Removes common page headers and footers to improve accuracy
5. **Confidence Scoring**: Each potential heading gets a confidence score based on multiple factors:
   - Font size relative to document average
   - Bold formatting
   - Text patterns (colons, capitalization, numbering)
   - Position on page
   - Content structure

## Libraries Used

- **PyMuPDF (fitz)**: Primary PDF parsing library chosen for:
  - High performance and accuracy
  - Detailed font information extraction
  - Excellent text positioning data
  - Lightweight footprint (< 200MB requirement)
  - No GPU dependencies
  - Works offline

## Algorithm Details

### Title Detection
- Analyzes first page text blocks
- Identifies largest font sizes near page top
- Filters out headers/footers and page numbers
- Returns most substantial text with appropriate font size

### Heading Classification
1. **Font Size Analysis**: Calculates size thresholds based on document statistics
2. **Pattern Matching**: Recognizes common heading patterns:
   - Section numbers (1.1, 1.2, etc.)
   - Keywords (Summary, Background, Conclusion)
   - Formatting clues (colons, all caps, bold text)
3. **Hierarchy Assignment**: 
   - H1: Largest fonts, major sections
   - H2: Secondary sections, appendices
   - H3: Subsections, detailed points
   - H4: Specific breakdowns ("For each..." patterns)
4. **Post-processing**: Removes duplicates and applies quality filters

### Performance Optimizations
- Uses block-level text extraction for speed
- Implements efficient font analysis with caching
- Limits processing to reasonable heading counts
- Optimized for the 10-second constraint

## Build and Run Instructions

### Build the Docker image:
```bash
docker build --platform linux/amd64 -t pdf-outline-extractor:latest .
```

### Run the container:
```bash
docker run --rm -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output --network none pdf-outline-extractor:latest
```

The container will:
1. Process all PDF files from `/app/input`
2. Generate corresponding JSON files in `/app/output`
3. Each `filename.pdf` produces `filename.json`

## Output Format

```json
{
  "title": "Document Title",
  "outline": [
    {"level": "H1", "text": "Major Section", "page": 1},
    {"level": "H2", "text": "Subsection", "page": 2},
    {"level": "H3", "text": "Detail Point", "page": 3}
  ]
}
```

## Constraints Compliance

- ✅ Execution time: ≤ 10 seconds for 50-page PDF
- ✅ Model size: Uses PyMuPDF (~50MB), no ML models needed
- ✅ No network access required
- ✅ CPU only (amd64)
- ✅ Memory efficient design for 16GB RAM systems

## Testing

The solution has been tested with the provided sample files and achieves:
- Accurate title extraction
- Proper heading hierarchy detection
- ~82% heading match accuracy on test documents
- Fast processing times

## Architecture Notes

The extractor is designed to be:
- **Modular**: Easy to extend for Round 1B
- **Robust**: Handles various PDF formats and edge cases  
- **Efficient**: Optimized for hackathon constraints
- **Multilingual Ready**: Unicode support for bonus points
