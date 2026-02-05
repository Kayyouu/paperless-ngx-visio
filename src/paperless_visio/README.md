# Paperless Visio Parser

Parser for Microsoft Visio files (.vsd and .vsdx) in Paperless-NGX.

## Features

- **Native .vsdx (OOXML) Parsing**: Uses the lightweight `vsdx` library for modern format files
- **PDF Conversion**: Converts both .vsd and .vsdx to PDF via LibreOffice for archival
- **Text Extraction**:
  - Direct: For .vsdx files using native parsing
  - PDF-based: For .vsd files and fallback via Tika
- **Thumbnail Generation**: Creates thumbnails from PDF first page or fallback placeholder
- **Automatic Integration**: Registers with document consumer system via Django signals

## Installation

### 1. Dependencies

The parser requires:

```bash
# Required
pip install vsdx

# Optional but recommended for PDF conversion
# LibreOffice (system package)
sudo apt install libreoffice libreoffice-draw  # Debian/Ubuntu
brew install libreoffice                        # macOS
choco install libreoffice                       # Windows

# Optional: For PDF text extraction
pip install tika-python
```

### 2. Django Configuration

The parser is already registered in `src/paperless/settings.py`:

```python
INSTALLED_APPS = [
    ...
    "paperless_visio.apps.PaperlessVisioConfig",
    ...
]
```

It has automatic logging configuration:

```python
LOGGING = {
    ...
    "handlers": {
        "file_visio": { ... },
    },
    "loggers": {
        "paperless_visio": {"handlers": ["file_visio"], "level": "DEBUG"},
    },
}
```

## Usage

### Import Files

#### Method 1: Consume Folder

Place Visio files in the consume folder:

```bash
cp diagram.vsdx /path/to/consume/
```

Paperless will automatically:
1. Detect the MIME type
2. Route to VisioDocumentParser (weight: 15)
3. Extract text (native or via PDF/Tika)
4. Generate PDF archive
5. Create thumbnail
6. Index the document

#### Method 2: Web Interface

Upload via the web UI:
1. Click "Upload"
2. Select .vsd or .vsdx file
3. File is processed automatically

#### Method 3: API

```bash
curl -X POST \
  -H "Authorization: Token YOUR_TOKEN" \
  -F "document=@diagram.vsdx" \
  http://localhost:8000/api/documents/
```

### Configuration

#### LibreOffice Path

If LibreOffice is not found in standard locations, the parser will search:
- Windows: `C:\Program Files\LibreOffice\program\soffice.exe`
- Linux: `/usr/bin/soffice`, `/usr/local/bin/soffice`
- Custom: Use `which soffice` to locate

To use custom path, edit [parsers.py](parsers.py) in `_find_libreoffice()` method.

#### Tika Server (Optional)

For better PDF text extraction, configure Tika:

```bash
# Start Tika server
docker run -d -p 9998:9998 apache/tika:latest
```

In `paperless.conf`:

```
PAPERLESS_TIKA_ENABLED=yes
PAPERLESS_TIKA_ENDPOINT=http://localhost:9998
```

## Supported MIME Types

| Format | MIME Type | Extension | Strategy |
|--------|-----------|-----------|----------|
| Modern Visio | `application/vnd.visio` | .vsdx | Native parsing + PDF |
| Legacy Visio | `application/x-visio` | .vsd | PDF conversion + Tika |
| Visio with Macros | `application/vnd.visio.drawing.macro` | .vsdm | Native parsing (read-only) |

Additional aliases supported:
- `application/vnd.microsoft.visio`
- `application/x-ms-visio`
- `application/msvisio`
- `application/vnd.visio.drawing`
- `application/vnd.visio.xml`

## How It Works

### 1. File Detection

```
.vsdx / .vsd → Magic MIME detection → document_consumer_declaration signal
```

### 2. Parser Selection

- Consumer sends signal to all registered parsers
- VisioDocumentParser declares: weight=15
- If Tika also supports it (weight=10), VisioDocumentParser takes priority
- Parser is instantiated and called

### 3. Text Extraction (VSDX)

```python
# Native parsing
vsdx.VisioFile(document_path)
  → Extract shapes → Extract text + data from all pages
  → Return combined text
```

### 4. Text Extraction (VSD)

```python
# Fallback for .vsd or if native fails
LibreOffice soffice
  → Convert to PDF (tempdir)
  → Try Tika extraction from PDF
  → Fallback to generic text
```

### 5. PDF Archive Generation

```python
# For both .vsd and .vsdx
LibreOffice soffice
  → Convert to PDF
  → Store in archive_path
  → Indexed for download
```

### 6. Thumbnail Generation

```python
# Strategy 1: From PDF
PDF first page → ImageMagick/pdf2image → PNG → WEBP

# Strategy 2: Placeholder (fallback)
PIL → Visio blue background → Text overlay → WEBP
```

## Troubleshooting

### Parser Not Detecting Visio Files

**Problem**: Files aren't recognized as Visio documents

**Solution**:
```bash
# Check MIME type detection
python -c "import magic; print(magic.from_file('diagram.vsdx', mime=True))"

# Verify parser registration
python manage.py shell
>>> from documents.parsers import get_parser_class_for_mime_type
>>> parser = get_parser_class_for_mime_type("application/vnd.visio")
>>> print(parser)  # Should show VisioDocumentParser
```

### No Text Extracted

**Problem**: Document has content but text field is empty

**Reason**:
- VSDX native parsing failed, fallback to PDF + Tika
- Tika not configured
- Text in shapes but not in standard places

**Solution**:
1. Check logs: `tail -f data/log/visio.log`
2. Enable Tika: See Configuration section
3. Convert .vsd to .vsdx if possible

### PDF Not Generated

**Problem**: Archive PDF missing

**Reason**:
- LibreOffice not found
- LibreOffice error during conversion

**Solution**:
1. Install LibreOffice: `sudo apt install libreoffice libreoffice-draw`
2. Check logs: `tail -f data/log/visio.log`
3. Test manually: `soffice --headless --convert-to pdf diagram.vsdx`

### Slow Processing

**Problem**: Visio files take long to process

**Reason**:
- LibreOffice PDF conversion is slow for large files
- Tika server slow or unresponsive

**Solution**:
1. Parallel processing: Configure `PAPERLESS_TASK_WORKERS`
2. Skip PDF archive: Set `self.archive_path = None` if not needed
3. Disable Tika: Simpler extraction without server overhead

## Architecture

### Class Hierarchy

```
DocumentParser (documents/parsers.py)
  └── VisioDocumentParser (paperless_visio/parsers.py)
      ├── _parse_vsdx_native()           # Native VSDX parsing
      ├── _parse_via_pdf_conversion()    # VSD/fallback
      ├── _extract_text_from_pdf_via_tika()  # Optional Tika
      ├── _generate_pdf_archive()        # PDF creation
      ├── _generate_thumbnail_from_pdf() # Thumbnail from PDF
      ├── _create_placeholder_thumbnail() # Fallback thumbnail
      └── _convert_to_pdf()              # LibreOffice command
```

### Signal Registration

```python
# signals.py
def visio_consumer_declaration(sender, **kwargs):
    return {
        "parser": get_parser,      # Factory function
        "weight": 15,              # Priority
        "mime_types": { ... }      # Supported formats
    }

# apps.py
class PaperlessVisioConfig(AppConfig):
    def ready(self):
        document_consumer_declaration.connect(visio_consumer_declaration)
```

## Performance Notes

### Text Extraction
- **VSDX native**: Very fast (~100-500ms)
- **VSD + PDF**: Slower (~2-5s) due to LibreOffice
- **PDF + Tika**: Medium (~1-3s) if Tika available

### PDF Generation
- **VSDX → PDF**: ~1-5 seconds via LibreOffice
- **VSD → PDF**: ~2-5 seconds via LibreOffice
- Can be large for complex diagrams

### Thumbnails
- **PDF → Image**: ~500ms if pdf2image available
- **Placeholder**: <100ms fallback

## Development

### Running Tests

```bash
# All tests
python manage.py test paperless_visio.tests

# Specific test
python manage.py test paperless_visio.tests.VisioDocumentParserTestCase.test_parse_vsdx_format

# With verbose output
python manage.py test paperless_visio.tests -v 2
```

### Adding Sample Files

Place test files in `tests/samples/`:

```bash
cp diagram.vsdx src/paperless_visio/tests/samples/
cp diagram.vsd src/paperless_visio/tests/samples/
```

### Extending the Parser

To add support for other Visio-related formats:

1. Update `MIME_TYPES` in `signals.py`
2. Add parsing method in `VisioDocumentParser`
3. Add tests in `test_parsers.py`

## Known Limitations

1. **.vsd binary format**: No pure Python parser exists
   - Requires LibreOffice or Aspose (commercial)
   - Fallback: Convert to .vsdx first

2. **Large diagrams**: May be slow/memory intensive
   - LibreOffice PDF conversion scales with complexity
   - Consider splitting very large documents

3. **Embedded objects**: Not extracted
   - Images in shapes are ignored
   - Only text content extracted

4. **Visio extensions**: Advanced features not supported
   - Add-on data not extracted
   - Custom properties may be missed

## References

- [vsdx Library](https://github.com/dave-howard/vsdx)
- [LibreOffice Draw](https://www.libreoffice.org/discover/draw/)
- [Paperless-NGX Parser Development](https://docs.paperless-ngx.com/development/#making-custom-parsers)
