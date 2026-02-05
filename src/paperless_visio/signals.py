"""
Signal handler for registering the Visio parser with the document consumer system

This module connects the VisioDocumentParser to Django's document_consumer_declaration
signal, making it available for processing .vsd and .vsdx files.
"""


def get_parser(*args, **kwargs):
    """
    Factory function to create a VisioDocumentParser instance

    This is called by the document consumer to instantiate the parser
    when a Visio file is detected.
    """
    from .parsers import VisioDocumentParser
    return VisioDocumentParser(*args, **kwargs)


def visio_consumer_declaration(sender, **kwargs):
    """
    Signal handler for document_consumer_declaration

    Declares support for Microsoft Visio file formats supported by Gotenberg.

    Weight: 15
    - Higher than Tika (10) to handle all Visio formats
    - Lower than Mail (20)

    Text Extraction Strategy:
    - VSDX/VSDM: Native text extraction via vsdx library (fast, ~100ms)
    - Other formats (VSD, VSTM, VDX):
      PDF conversion via LibreOffice/Gotenberg + text extraction from PDF

    Supported Formats:
    - VSDX: Drawing (modern OOXML) - Native extraction
    - VSDM: Drawing with macros (modern OOXML) - Native extraction
    - VSTM: Template with macros - PDF extraction
    - VSD: Legacy binary format - PDF extraction
    - VDX: Legacy XML format - PDF extraction

    Unsupported by Gotenberg (not included):
    - VSTX, VST, VSSX, VSSM, VSS, VDW
    """
    return {
        "parser": get_parser,
        "weight": 15,
        "mime_types": {
            # Modern OOXML Drawing Formats (Visio 2013+) - Native text extraction
            "application/vnd.ms-visio.drawing.main+xml": ".vsdx",
            "application/vnd.ms-visio.drawing.macroEnabled.main+xml": ".vsdm",
            # Modern OOXML Templates (macro-enabled only) - PDF conversion
            "application/vnd.ms-visio.template.macroEnabled.main+xml": ".vstm",
            # Legacy Binary Formats - PDF conversion
            "application/vnd.visio": ".vsd",
            "application/vnd.microsoft.visio": ".vsd",
            "application/x-visio": ".vsd",
            "application/x-ms-visio": ".vsd",
            "application/msvisio": ".vsd",
            "application/vnd.ms-office": ".vsd",  # Generic MS Office MIME type
            # Legacy XML Formats - PDF conversion
            "application/vnd.visio.xml": ".vdx",
            "application/visio": ".vdx",
            "application/visio.drawing": ".vdx",
            "text/xml": ".vdx",  # VDX files detected as text/xml
        },
    }
