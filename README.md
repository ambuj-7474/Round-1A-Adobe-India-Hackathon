# PDF Outline Extractor

A robust tool for extracting structured outlines from PDF documents. This project identifies document titles and hierarchical headings (H1, H2, H3) along with their corresponding page numbers, outputting the results in a structured JSON format.

## Features

- **Accurate Title Extraction**: Identifies document titles from metadata or content analysis
- **Hierarchical Heading Detection**: Classifies headings into H1, H2, and H3 levels
- **Page Number Mapping**: Associates each heading with its correct page number
- **Multilingual Support**: Fully supports documents in multiple languages including English, Japanese, Hindi, and other non-Latin scripts
- **Performance Optimized**: Processes documents efficiently within time constraints
- **Containerized**: Runs in an isolated Docker environment

## Requirements

- Docker

## Usage

### Building the Docker Image

```bash
docker build -t pdf-outline-extractor .
```

### Running the Container

```bash
docker run --rm -v /path/to/input:/app/input -v /path/to/output:/app/output pdf-outline-extractor
```

Replace `/path/to/input` with the directory containing your PDF files and `/path/to/output` with the directory where you want the JSON results to be saved.

### Processing a Single PDF

```bash
docker run --rm -v /path/to/pdf:/app/input/document.pdf -v /path/to/output:/app/output pdf-outline-extractor
```

## Output Format

The extractor generates a JSON file with the following structure:

```json
{
    "title": "Document Title",
    "outline": [
        {"text": "Heading 1", "level": "H1", "page": 1},
        {"text": "Heading 2", "level": "H2", "page": 2},
        ...
    ]
}
```

## Technical Details

### Heading Detection

The system uses a combination of heuristics to identify headings:

- Font size analysis relative to document average
- Text formatting (bold, all caps)
- Numbering patterns (e.g., "1.", "1.1", "Chapter 1")
- Text length and content analysis

### Heading Level Classification

Headings are classified into levels based on:

- Font size hierarchy within the document
- Numbering patterns (e.g., "1." for H1, "1.1" for H2)
- Semantic analysis of text content
- Formatting characteristics

### Multilingual Support

The PDF Outline Extractor provides robust support for multilingual documents through several key features:

1. **Unicode-aware Text Processing**: 
   - Uses Unicode normalization (NFKC) with special handling for CJK (Chinese, Japanese, Korean) and Indic scripts
   - Preserves script-specific characters while removing control characters
   - Handles text directionality (RTL and LTR scripts)

2. **Language-Agnostic Heading Detection**:
   - Adapts text length evaluation based on character width categories (wide characters in CJK scripts count differently)
   - Recognizes chapter/section markers in multiple languages (e.g., "章" in Japanese, "अध्याय" in Hindi)
   - Detects special Unicode numbering and bullet characters used in non-Latin documents

3. **Script-Aware Title Extraction**:
   - Handles vertical text layouts common in East Asian documents
   - Adjusts title length thresholds based on script characteristics
   - Recognizes title patterns across different writing systems

4. **Adaptive Font Analysis**:
   - Uses relative font sizing that works regardless of language
   - Relies more on formatting (bold, size) for scripts where capitalization doesn't apply
   - Identifies heading patterns specific to different writing systems

The extractor has been tested with documents in English, Japanese, Hindi, and other languages with non-Latin scripts to ensure consistent performance across different writing systems.

### Performance Optimization

- Limits processing to a maximum number of pages
- Uses efficient text extraction methods
- Implements performance tracking for bottleneck identification

## Project Structure

```
.
├── Dockerfile          # Container configuration
├── process_pdfs.py     # Main processing script
├── requirements.txt    # Python dependencies
└── README.md           # Documentation
```

## Dependencies

- PyMuPDF: PDF parsing and text extraction
- tqdm: Progress bar visualization

## License

MIT