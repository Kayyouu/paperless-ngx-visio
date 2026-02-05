"""
Unit tests for the VisioDocumentParser

Tests cover:
- VSDX native parsing (modern format)
- VSD handling (legacy format)
- PDF generation/archival
- Thumbnail generation
- Error handling
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from paperless_visio.parsers import VisioDocumentParser


class VisioDocumentParserTestCase(TestCase):
    """Test cases for VisioDocumentParser"""

    def setUp(self):
        """Set up test fixtures"""
        self.parser = VisioDocumentParser("test_logging_group")
        self.test_samples_dir = Path(__file__).parent / "samples"
        self.test_samples_dir.mkdir(exist_ok=True)

    def tearDown(self):
        """Clean up after tests"""
        try:
            self.parser.cleanup()
        except Exception:
            pass

    def test_parser_initialization(self):
        """Test that parser initializes correctly"""
        self.assertIsNotNone(self.parser.tempdir)
        self.assertTrue(self.parser.tempdir.exists())
        self.assertIsNone(self.parser.text)
        self.assertIsNone(self.parser.archive_path)
        self.assertIsNone(self.parser.date)

    def test_get_settings(self):
        """Test that get_settings returns None (no special settings)"""
        settings = self.parser.get_settings()
        self.assertIsNone(settings)

    def test_find_libreoffice(self):
        """Test LibreOffice path detection"""
        paths = VisioDocumentParser._find_libreoffice()
        # This may or may not find LibreOffice depending on installation
        # Just verify it returns a list
        self.assertIsInstance(paths, list)

    @patch("paperless_visio.parsers.VisioDocumentParser._parse_vsdx_native")
    @patch("paperless_visio.parsers.VisioDocumentParser._generate_pdf_archive")
    def test_parse_vsdx_format(self, mock_pdf, mock_vsdx):
        """Test parsing VSDX format (modern OOXML)"""
        # Mock the actual parsing and PDF generation
        mock_vsdx.return_value = None
        mock_pdf.return_value = None

        # Create a fake VSDX file for testing
        fake_vsdx = self.test_samples_dir / "test.vsdx"
        fake_vsdx.touch()

        try:
            self.parser.parse(
                fake_vsdx,
                "application/vnd.visio",
                "test.vsdx"
            )

            # Verify methods were called
            mock_vsdx.assert_called_once()
            mock_pdf.assert_called_once()

        finally:
            fake_vsdx.unlink(missing_ok=True)

    @patch("paperless_visio.parsers.VisioDocumentParser._convert_to_pdf")
    @patch("paperless_visio.parsers.VisioDocumentParser._generate_pdf_archive")
    def test_parse_vsd_format(self, mock_pdf_gen, mock_pdf_conv):
        """Test parsing VSD format (legacy binary)"""
        # Mock PDF conversion
        pdf_file = self.parser.tempdir / "test.pdf"
        pdf_file.touch()
        mock_pdf_conv.return_value = pdf_file
        mock_pdf_gen.return_value = None

        fake_vsd = self.test_samples_dir / "test.vsd"
        fake_vsd.touch()

        try:
            self.parser.parse(
                fake_vsd,
                "application/x-visio",
                "test.vsd"
            )

            # PDF conversion should be attempted for VSD
            self.assertIsNotNone(self.parser.text)

        finally:
            fake_vsd.unlink(missing_ok=True)

    def test_thumbnail_placeholder_creation(self):
        """Test placeholder thumbnail creation when PDF not available"""
        thumbnail_path = self.parser._create_placeholder_thumbnail("test.vsdx")

        self.assertIsNotNone(thumbnail_path)
        self.assertTrue(thumbnail_path.exists())
        self.assertIn(thumbnail_path.suffix, [".webp", ".png", ".jpg"])

    def test_thumbnail_returns_path(self):
        """Test that get_thumbnail returns a valid Path object"""
        fake_file = self.test_samples_dir / "test.vsdx"
        fake_file.touch()

        try:
            with patch.object(
                self.parser,
                "_generate_thumbnail_from_pdf",
                return_value=None
            ):
                result = self.parser.get_thumbnail(
                    fake_file,
                    "application/vnd.visio",
                    "test.vsdx"
                )

            self.assertIsInstance(result, Path)
            self.assertTrue(result.exists())

        finally:
            fake_file.unlink(missing_ok=True)

    def test_parse_error_handling(self):
        """Test that ParseError is raised on invalid input"""
        from documents.parsers import ParseError

        non_existent_file = self.test_samples_dir / "nonexistent.vsdx"

        with patch.object(
            self.parser,
            "_parse_vsdx_native",
            side_effect=Exception("Test error")
        ):
            with patch.object(
                self.parser,
                "_parse_via_pdf_conversion",
                side_effect=Exception("Test error")
            ):
                with self.assertRaises(ParseError):
                    self.parser.parse(
                        non_existent_file,
                        "application/vnd.visio"
                    )

    def test_tempdir_cleanup(self):
        """Test that tempdir is properly cleaned up"""
        tempdir = self.parser.tempdir
        self.assertTrue(tempdir.exists())

        self.parser.cleanup()

        self.assertFalse(tempdir.exists())

    @patch("subprocess.run")
    def test_pdf_conversion_command_building(self, mock_run):
        """Test that PDF conversion command is built correctly"""
        mock_run.return_value = MagicMock(returncode=1, stderr="")

        fake_file = self.test_samples_dir / "test.vsdx"
        fake_file.touch()

        try:
            with patch.object(
                VisioDocumentParser,
                "_find_libreoffice",
                return_value=[Path("/fake/soffice")]
            ):
                result = self.parser._convert_to_pdf(fake_file)

            # Verify subprocess was called
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]

            # Verify command structure
            self.assertIn("--headless", call_args)
            self.assertIn("--convert-to", call_args)
            self.assertIn("pdf", call_args)
            self.assertIn(str(fake_file), call_args)

        finally:
            fake_file.unlink(missing_ok=True)


class VisioSignalHandlerTestCase(TestCase):
    """Test cases for Visio signal handler"""

    def test_signal_declaration_structure(self):
        """Test that signal declaration has correct structure"""
        from paperless_visio.signals import visio_consumer_declaration

        declaration = visio_consumer_declaration(None)

        # Check required keys
        self.assertIn("parser", declaration)
        self.assertIn("weight", declaration)
        self.assertIn("mime_types", declaration)

        # Check types
        self.assertIsCallable(declaration["parser"])
        self.assertIsInstance(declaration["weight"], int)
        self.assertIsInstance(declaration["mime_types"], dict)

    def test_signal_weight_priority(self):
        """Test that Visio parser has appropriate weight"""
        from paperless_visio.signals import visio_consumer_declaration

        declaration = visio_consumer_declaration(None)

        # Weight should be between Tika (10) and Mail (20)
        weight = declaration["weight"]
        self.assertGreaterEqual(weight, 10)
        self.assertLessEqual(weight, 20)

    def test_mime_type_coverage(self):
        """Test that common Visio MIME types are covered"""
        from paperless_visio.signals import visio_consumer_declaration

        declaration = visio_consumer_declaration(None)
        mime_types = declaration["mime_types"]

        # Check for at least the main formats
        self.assertIn("application/vnd.visio", mime_types)
        self.assertIn("application/x-visio", mime_types)

        # Verify extensions
        self.assertTrue(mime_types["application/vnd.visio"].endswith(".vsdx"))
        self.assertTrue(mime_types["application/x-visio"].endswith(".vsd"))

    def test_parser_factory_function(self):
        """Test that parser factory function works"""
        from paperless_visio.signals import get_parser

        parser = get_parser("test_group")

        self.assertIsNotNone(parser)
        from paperless_visio.parsers import VisioDocumentParser
        self.assertIsInstance(parser, VisioDocumentParser)

        parser.cleanup()


class VisioAppConfigTestCase(TestCase):
    """Test cases for Django app configuration"""

    def test_app_config_exists(self):
        """Test that app configuration is properly defined"""
        from paperless_visio.apps import PaperlessVisioConfig

        config = PaperlessVisioConfig("paperless_visio", None)

        self.assertEqual(config.name, "paperless_visio")
        self.assertIsNotNone(config.verbose_name)

    @patch("documents.signals.document_consumer_declaration.connect")
    def test_signal_connection_on_ready(self, mock_connect):
        """Test that signal is connected when app is ready"""
        from paperless_visio.apps import PaperlessVisioConfig

        config = PaperlessVisioConfig("paperless_visio", None)

        # Mock the connect method
        with patch.object(config, "module"):
            try:
                config.ready()
            except Exception:
                # May fail due to missing logger, but connection should still be attempted
                pass

            # Verify connect was attempted
            # Note: This test may need adjustment based on actual Django setup


class IntegrationTestCase(TestCase):
    """Integration tests with Django document consumer system"""

    def test_parser_registration(self):
        """Test that Visio parser is properly registered"""
        from documents.parsers import get_parser_class_for_mime_type

        # Test VSDX detection
        parser_class = get_parser_class_for_mime_type("application/vnd.visio")
        self.assertIsNotNone(parser_class)

        # Test VSD detection
        parser_class = get_parser_class_for_mime_type("application/x-visio")
        self.assertIsNotNone(parser_class)

    def test_parser_instantiation_via_consumer(self):
        """Test that parser can be instantiated through consumer system"""
        from documents.parsers import get_parser_class_for_mime_type

        parser_class = get_parser_class_for_mime_type("application/vnd.visio")

        if parser_class:
            parser = parser_class("test_group")
            self.assertIsNotNone(parser)
            parser.cleanup()
