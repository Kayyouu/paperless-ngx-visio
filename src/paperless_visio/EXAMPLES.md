# Visio Parser - Usage Examples

Practical examples of using the Visio parser in Paperless-NGX.

## Basic Usage

### 1. Import via Consume Folder

```bash
# Copy a Visio file to the consume folder
cp my_diagram.vsdx ~/paperless/consume/

# Paperless automatically processes it
# Check logs to see progress
tail -f ~/paperless/data/log/visio.log
```

**Output**:
- Document indexed with extracted text
- PDF archive generated
- Thumbnail displayed in UI

### 2. Import via Web Interface

1. Open Paperless: http://localhost:8000
2. Click "Upload" button
3. Select a .vsd or .vsdx file
4. Document appears in library after processing

### 3. Import via API

```bash
# Using curl
curl -X POST \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -F "document=@network_diagram.vsdx" \
  http://localhost:8000/api/documents/

# Response includes document ID and metadata
{
  "id": 123,
  "filename": "network_diagram.vsdx",
  "content": "System Design\nDatabase\nAPI Server\n...",
  ...
}
```

### 4. Bulk Import

```bash
#!/bin/bash
# Import all Visio files from a directory

SOURCE_DIR="/path/to/diagrams"
CONSUME_DIR="/path/to/paperless/consume"

for file in "$SOURCE_DIR"/*.vsdx "$SOURCE_DIR"/*.vsd; do
  if [ -f "$file" ]; then
    echo "Processing: $file"
    cp "$file" "$CONSUME_DIR/"
    sleep 2  # Wait for processing
  fi
done

echo "Bulk import complete"
```

## Python API Usage

### Django Shell Examples

```bash
python manage.py shell
```

#### Example 1: Get a Visio Document

```python
from documents.models import Document

# Find Visio documents
visio_docs = Document.objects.filter(filename__endswith='.vsdx')

for doc in visio_docs:
    print(f"Document: {doc.filename}")
    print(f"Content: {doc.content[:200]}...")  # First 200 chars
    print(f"Archive: {doc.archive_filename}")
    print()
```

#### Example 2: Extract Text from Visio

```python
from documents.models import Document

doc = Document.objects.get(filename='diagram.vsdx')

# Get extracted text
text = doc.content
print(f"Extracted text ({len(text)} chars):")
print(text)

# Search for specific content
if "Database" in text:
    print("Found 'Database' in diagram")
```

#### Example 3: Access PDF Archive

```python
from documents.models import Document
from pathlib import Path

doc = Document.objects.get(filename='diagram.vsdx')

# Check if PDF was generated
if doc.archive_filename:
    archive_path = Path(doc.get_archive_path())
    print(f"Archive size: {archive_path.stat().st_size / 1024:.1f} KB")

    # Read PDF metadata
    print(f"Archive path: {archive_path}")
else:
    print("No PDF archive generated")
```

#### Example 4: Search Visio Documents

```python
from documents.models import Document

# Search by content
results = Document.objects.filter(
    content__contains='System Design'
)

print(f"Found {results.count()} diagrams with 'System Design'")

for doc in results:
    print(f"  - {doc.filename}")
```

## Advanced Usage

### Direct Parser Usage

```python
from pathlib import Path
from paperless_visio.parsers import VisioDocumentParser

# Create parser instance
parser = VisioDocumentParser(logging_group="test")

# Parse a file
visio_file = Path("diagram.vsdx")
parser.parse(visio_file, "application/vnd.visio")

# Get results
text = parser.get_text()
thumbnail = parser.get_thumbnail(visio_file, "application/vnd.visio")
archive = parser.archive_path

print(f"Text: {text}")
print(f"Thumbnail: {thumbnail}")
print(f"Archive PDF: {archive}")

# Cleanup
parser.cleanup()
```

### Testing with Sample Files

```python
import tempfile
from pathlib import Path
from paperless_visio.parsers import VisioDocumentParser
from documents.parsers import ParseError

# Create a test Visio file (mock)
with tempfile.NamedTemporaryFile(suffix='.vsdx', delete=False) as f:
    test_file = Path(f.name)

parser = VisioDocumentParser("test")

try:
    parser.parse(test_file, "application/vnd.visio")
    print(f"Extracted text: {parser.text}")
except ParseError as e:
    print(f"Parse error: {e}")
finally:
    parser.cleanup()
    test_file.unlink()
```

## Integration with Other Systems

### 1. Automatic Processing Hook

```python
# Add to documents/signals/handlers.py

from django.dispatch import receiver
from documents.signals import document_consumption_finished
from documents.models import Document

@receiver(document_consumption_finished)
def process_visio_after_import(sender, document, **kwargs):
    """Hook: Process Visio documents after import"""

    if document.filename.endswith(('.vsdx', '.vsd')):
        # Custom logic for Visio documents
        print(f"Processing Visio: {document.filename}")

        # Example: Add special tag
        if "Database" in document.content:
            document.tags.add(tag_name="architecture")
            document.save()
```

### 2. REST API Integration

```bash
#!/bin/bash
# Script to import and retrieve Visio documents via API

API_URL="http://localhost:8000/api"
TOKEN="your-api-token"

# Upload file
RESPONSE=$(curl -s -X POST \
  -H "Authorization: Token $TOKEN" \
  -F "document=@diagram.vsdx" \
  "$API_URL/documents/")

# Extract document ID
DOC_ID=$(echo "$RESPONSE" | grep -o '"id":[0-9]*' | cut -d: -f2)

# Get document details
curl -s -H "Authorization: Token $TOKEN" \
  "$API_URL/documents/$DOC_ID/" | jq .

# Download thumbnail
curl -s -H "Authorization: Token $TOKEN" \
  "$API_URL/documents/$DOC_ID/thumb/" > thumbnail.png

# Get content snippet
curl -s -H "Authorization: Token $TOKEN" \
  "$API_URL/documents/$DOC_ID/" | jq '.content' | head -c 500
```

### 3. Automatic Tag Assignment

```python
# documents/signals/handlers.py

from django.dispatch import receiver
from documents.signals import document_consumption_finished
from documents.models import Document, Tag

@receiver(document_consumption_finished)
def auto_tag_visio_by_content(sender, document, **kwargs):
    """Auto-tag Visio documents based on content"""

    if not document.filename.endswith(('.vsdx', '.vsd')):
        return

    keywords = {
        'diagram': 'diagrams',
        'architecture': 'it-architecture',
        'network': 'networking',
        'database': 'databases',
        'workflow': 'workflows',
        'process': 'processes',
        'system': 'systems',
    }

    content = document.content.lower()

    for keyword, tag_name in keywords.items():
        if keyword in content:
            tag, _ = Tag.objects.get_or_create(name=tag_name)
            document.tags.add(tag)

    if document.tags.exists():
        print(f"Tagged {document.filename} with: {', '.join(t.name for t in document.tags.all())}")
```

## CLI Usage

### Bulk Processing

```bash
#!/bin/bash
# Process all Visio files in a directory with progress

CONSUME_DIR="/path/to/paperless/consume"

echo "Processing Visio files..."

count=0
for file in *.vsdx *.vsd; do
  if [ -f "$file" ]; then
    echo "Copying: $file"
    cp "$file" "$CONSUME_DIR/"
    count=$((count + 1))

    # Optional: Show progress
    echo "  ($count files copied)"
  fi
done

echo "Done! $count files ready for processing"
```

### Manual Document Processing

```bash
#!/bin/bash
# Manually test parser with a file

python manage.py shell << EOF
from pathlib import Path
from paperless_visio.parsers import VisioDocumentParser

file = Path("$1")  # Pass filename as argument

if not file.exists():
    print(f"File not found: {file}")
    exit(1)

parser = VisioDocumentParser("manual_test")

try:
    parser.parse(file, "application/vnd.visio")
    print(f"✓ Text extracted ({len(parser.text)} chars)")
    print(f"\nContent preview:")
    print(parser.text[:500])

    if parser.archive_path:
        print(f"\n✓ PDF generated: {parser.archive_path}")

except Exception as e:
    print(f"✗ Error: {e}")

finally:
    parser.cleanup()
EOF
```

Usage:
```bash
chmod +x test_visio.sh
./test_visio.sh diagram.vsdx
```

## Debugging

### Enable Debug Logging

```bash
# In paperless.conf or environment
export PAPERLESS_DEBUG=true
export LOGLEVEL=DEBUG
```

Then:
```bash
# Watch parser logs
tail -f data/log/visio.log

# Example output:
# [2024-01-15 10:23:45] [DEBUG] [paperless_visio.parsers] Processing VSDX: diagram.vsdx
# [2024-01-15 10:23:45] [DEBUG] [paperless_visio.parsers] Found page: Page-1
# [2024-01-15 10:23:46] [DEBUG] [paperless_visio.parsers] Extracted 45 shapes
# [2024-01-15 10:23:48] [INFO] [paperless_visio.parsers] Generated PDF archive
```

### Check Parser Installation

```bash
python manage.py shell << EOF
from documents.parsers import get_parser_class_for_mime_type

# Check registration
parser = get_parser_class_for_mime_type("application/vnd.visio")
print(f"Parser for VSDX: {parser}")

parser = get_parser_class_for_mime_type("application/x-visio")
print(f"Parser for VSD: {parser}")

# Check if correct
from paperless_visio.parsers import VisioDocumentParser
assert parser == VisioDocumentParser, "Wrong parser!"
print("✓ Parser registered correctly")
EOF
```

## Performance Testing

### Benchmark Script

```bash
#!/bin/bash
# Measure parsing performance

python manage.py shell << EOF
import time
from pathlib import Path
from paperless_visio.parsers import VisioDocumentParser

files = [
    "simple.vsdx",
    "complex.vsdx",
    "legacy.vsd",
]

for file_name in files:
    if not Path(file_name).exists():
        print(f"Skipping {file_name} (not found)")
        continue

    parser = VisioDocumentParser("benchmark")

    start = time.time()
    try:
        parser.parse(Path(file_name), "application/vnd.visio")
        elapsed = time.time() - start

        print(f"{file_name}: {elapsed:.2f}s")
        print(f"  - Text size: {len(parser.text or '')} chars")
        print(f"  - Archive: {'Yes' if parser.archive_path else 'No'}")
    except Exception as e:
        print(f"{file_name}: ERROR - {e}")
    finally:
        parser.cleanup()
EOF
```

## Best Practices

### 1. File Organization

```
paperless/
├── consume/
│   └── visio/           # Visio subfolder
│       ├── diagrams/
│       └── architectures/
├── data/
└── ...
```

### 2. Naming Convention

```
# Good names (searchable)
- "2024-01-System-Architecture.vsdx"
- "Network-Topology-v2.vsd"
- "Database-Design-Production.vsdx"

# Poor names (not searchable)
- "Diagram1.vsdx"
- "New File.vsd"
- "copy_of_copy.vsdx"
```

### 3. Document Preprocessing

```bash
#!/bin/bash
# Clean and organize Visio files before import

# Remove temporary files
find . -name "~*.vsd*" -delete

# Fix file extensions
for file in *.visio; do
  mv "$file" "${file%.visio}.vsdx"
done

# Copy to consume folder
cp *.vsdx ~/paperless/consume/
```

## Troubleshooting Examples

### Example 1: File Not Recognized

```bash
# Check MIME type
file -i diagram.vsdx
# Output: diagram.vsdx: application/vnd.visio; charset=binary

# If wrong MIME type, rename:
mv diagram.something diagram.vsdx

# Check magic library
python -c "import magic; print(magic.from_file('diagram.vsdx', mime=True))"
```

### Example 2: No Text Extracted

```bash
# Test parser directly
python manage.py shell << EOF
from pathlib import Path
from paperless_visio.parsers import VisioDocumentParser

parser = VisioDocumentParser("test")
parser.parse(Path("diagram.vsdx"), "application/vnd.visio")

if parser.text:
    print(f"✓ Text extracted: {len(parser.text)} chars")
else:
    print("✗ No text extracted")

    # Check if parsing method was attempted
    print(f"Archive path: {parser.archive_path}")

parser.cleanup()
EOF
```

### Example 3: Slow Processing

```bash
# Check if LibreOffice is the bottleneck
time soffice --headless --convert-to pdf diagram.vsdx

# If slow, consider:
# 1. Increase task workers
# 2. Skip PDF generation (edit parser)
# 3. Use simpler diagrams
```

## References

- See [README.md](README.md) for technical details
- See [../../INTEGRATION.md](../../INTEGRATION.md) for architecture
- See [../../VISIO_SETUP.md](../../VISIO_SETUP.md) for installation
