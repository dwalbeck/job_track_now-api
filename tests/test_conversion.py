import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
from fastapi import Depends
import os
import tempfile
from app.utils.conversion import Conversion
from app.middleware.auth_middleware import get_current_user


class TestConversionHelpers:
    """Test suite for Conversion helper methods."""

    def test_get_file_path(self):
        """Test _get_file_path constructs correct path."""
        file_path = Conversion._get_file_path("test_file.docx")

        assert isinstance(file_path, Path)
        assert file_path.name == "test_file.docx"
        assert str(file_path).endswith("test_file.docx")


class TestMarkdownToHtml:
    """Test suite for _markdown_to_html method."""

    def test_markdown_to_html_basic(self):
        """Test basic markdown to HTML conversion."""
        markdown_content = "# Hello World\n\nThis is a **test**."

        html = Conversion._markdown_to_html(markdown_content)

        assert "<h1>Hello World</h1>" in html
        assert "<strong>test</strong>" in html
        assert "<!DOCTYPE html>" in html
        assert "<html>" in html

    def test_markdown_to_html_with_lists(self):
        """Test markdown with lists converts to HTML."""
        markdown_content = "- Item 1\n- Item 2\n- Item 3"

        html = Conversion._markdown_to_html(markdown_content)

        assert "<li>Item 1</li>" in html
        assert "<li>Item 2</li>" in html
        assert "<ul>" in html

    def test_markdown_to_html_with_code(self):
        """Test markdown with code blocks."""
        markdown_content = "```python\nprint('hello')\n```"

        html = Conversion._markdown_to_html(markdown_content)

        assert "<code>" in html or "<pre>" in html

    def test_markdown_to_html_empty_string(self):
        """Test markdown to HTML with empty string."""
        html = Conversion._markdown_to_html("")

        assert "<!DOCTYPE html>" in html
        assert "<html>" in html


class TestOdtConversions:
    """Test suite for ODT conversion methods."""

    @patch('subprocess.run')
    def test_odtToMd_success(self, mock_run):
        """Test ODT to Markdown conversion success."""
        mock_run.return_value = Mock(stdout="# Markdown Content", returncode=0)

        with tempfile.NamedTemporaryFile(suffix='.odt', delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(b"fake odt content")

        try:
            # Mock the file path resolution
            with patch.object(Conversion, '_get_file_path', return_value=Path(tmp_path)):
                result = Conversion.odtToMd("test.odt")

                assert result == "# Markdown Content"
                mock_run.assert_called_once()
                assert 'pandoc' in mock_run.call_args[0][0]
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @patch('subprocess.run')
    def test_odtToMd_file_not_found(self, mock_run):
        """Test ODT to Markdown with non-existent file."""
        with patch.object(Conversion, '_get_file_path', return_value=Path('/nonexistent/file.odt')):
            with pytest.raises(Exception, match="File not found"):
                Conversion.odtToMd("nonexistent.odt")

    @patch('subprocess.run')
    def test_odtToHtml_success(self, mock_run):
        """Test ODT to HTML conversion success."""
        mock_run.return_value = Mock(stdout="<html><body>Content</body></html>", returncode=0)

        with tempfile.NamedTemporaryFile(suffix='.odt', delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(b"fake odt content")

        try:
            with patch.object(Conversion, '_get_file_path', return_value=Path(tmp_path)):
                result = Conversion.odtToHtml("test.odt")

                assert "<html>" in result
                mock_run.assert_called_once()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestDocxConversions:
    """Test suite for DOCX conversion methods."""

    @patch('app.utils.conversion.do_convert')
    def test_docxToMd_success(self, mock_convert):
        """Test DOCX to Markdown conversion success."""
        mock_convert.return_value = "# Markdown Content"

        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(b"fake docx content")

        try:
            with patch.object(Conversion, '_get_file_path', return_value=Path(tmp_path)):
                result = Conversion.docxToMd("test.docx")

                assert result == "# Markdown Content"
                mock_convert.assert_called_once()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @patch('app.utils.conversion.do_convert')
    def test_docxToMd_file_not_found(self, mock_convert):
        """Test DOCX to Markdown with non-existent file."""
        with patch.object(Conversion, '_get_file_path', return_value=Path('/nonexistent/file.docx')):
            with pytest.raises(Exception, match="File not found"):
                Conversion.docxToMd("nonexistent.docx")


class TestPdfConversions:
    """Test suite for PDF conversion methods."""

    @patch('app.utils.conversion.MarkItDown')
    def test_pdfToMd_success(self, mock_markitdown_class):
        """Test PDF to Markdown conversion success."""
        mock_md_instance = Mock()
        mock_result = Mock()
        mock_result.text_content = "# PDF Content"
        mock_md_instance.convert.return_value = mock_result
        mock_markitdown_class.return_value = mock_md_instance

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(b"fake pdf content")

        try:
            with patch.object(Conversion, '_get_file_path', return_value=Path(tmp_path)):
                result = Conversion.pdfToMd("test.pdf")

                assert result == "# PDF Content"
                mock_md_instance.convert.assert_called_once()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @patch('app.utils.conversion.MarkItDown')
    def test_pdfToMd_file_not_found(self, mock_markitdown_class):
        """Test PDF to Markdown with non-existent file."""
        with patch.object(Conversion, '_get_file_path', return_value=Path('/nonexistent/file.pdf')):
            with pytest.raises(FileNotFoundError):
                Conversion.pdfToMd("nonexistent.pdf")

    @patch('app.utils.conversion.MarkItDown')
    @patch.object(Conversion, '_markdown_to_html')
    def test_pdfToHtml_success(self, mock_md_to_html, mock_markitdown_class):
        """Test PDF to HTML conversion success."""
        # Mock MarkItDown
        mock_md_instance = Mock()
        mock_result = Mock()
        mock_result.text_content = "# PDF Content"
        mock_md_instance.convert.return_value = mock_result
        mock_markitdown_class.return_value = mock_md_instance

        # Mock markdown to HTML conversion
        mock_md_to_html.return_value = "<html><h1>PDF Content</h1></html>"

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(b"fake pdf content")

        try:
            with patch.object(Conversion, '_get_file_path', return_value=Path(tmp_path)):
                result = Conversion.pdfToHtml("test.pdf")

                assert "<html>" in result
                mock_md_to_html.assert_called_once_with("# PDF Content")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestMarkdownConversions:
    """Test suite for Markdown conversion methods."""

    def test_mdToHtml_success(self):
        """Test Markdown to HTML conversion."""
        markdown_content = "# Test\n\nParagraph with **bold** text."

        result = Conversion.mdToHtml(markdown_content)

        assert "<h1>Test</h1>" in result
        assert "<strong>bold</strong>" in result
        assert "<!DOCTYPE html>" in result

    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    def test_md2docx_success(self, mock_tempfile, mock_run):
        """Test Markdown to DOCX conversion success."""
        # Mock temporary file
        mock_temp = MagicMock()
        mock_temp.name = '/tmp/test.md'
        mock_temp.__enter__.return_value = mock_temp
        mock_tempfile.return_value = mock_temp

        # Mock subprocess
        mock_run.return_value = Mock(returncode=0)

        # Mock output path
        with patch.object(Conversion, '_get_file_path', return_value=Path('/tmp/output.docx')):
            with patch('os.makedirs'):
                result = Conversion.md2docx("# Test Content", "output.docx")

                assert result == '/tmp/output.docx'
                mock_run.assert_called_once()

    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    def test_md2docx_with_reference_file(self, mock_tempfile, mock_run):
        """Test Markdown to DOCX with reference file."""
        # Mock temporary file
        mock_temp = MagicMock()
        mock_temp.name = '/tmp/test.md'
        mock_temp.__enter__.return_value = mock_temp
        mock_tempfile.return_value = mock_temp

        # Mock subprocess
        mock_run.return_value = Mock(returncode=0)

        # Mock paths
        output_path = Path('/tmp/output.docx')
        reference_path = Path('/tmp/reference.docx')

        with patch.object(Conversion, '_get_file_path') as mock_get_path:
            def get_path_side_effect(filename):
                if filename == "output.docx":
                    return output_path
                elif filename == "reference.docx":
                    return reference_path
                return Path(filename)

            mock_get_path.side_effect = get_path_side_effect

            with patch('os.makedirs'):
                with patch('os.path.exists', return_value=True):
                    result = Conversion.md2docx("# Test", "output.docx", "reference.docx")

                    assert result == str(output_path)
                    # Verify --reference-doc was used
                    call_args = mock_run.call_args[0][0]
                    assert '--reference-doc' in call_args

    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    def test_md2odt_success(self, mock_tempfile, mock_run):
        """Test Markdown to ODT conversion success."""
        # Mock temporary file
        mock_temp = MagicMock()
        mock_temp.name = '/tmp/test.md'
        mock_temp.__enter__.return_value = mock_temp
        mock_tempfile.return_value = mock_temp

        # Mock subprocess
        mock_run.return_value = Mock(returncode=0)

        with patch.object(Conversion, '_get_file_path', return_value=Path('/tmp/output.odt')):
            with patch('os.makedirs'):
                result = Conversion.md2odt("# Test Content", "output.odt")

                assert result == '/tmp/output.odt'
                mock_run.assert_called_once()


class TestPageFormatting:
    """Test suite for pageFormatting method."""

    @patch('app.utils.conversion.Document')
    def test_page_formatting_success(self, mock_document_class):
        """Test page formatting applies correctly."""
        # Create mock document with sections and paragraphs
        mock_doc = MagicMock()
        mock_section = MagicMock()
        mock_doc.sections = [mock_section]

        # Create mock paragraphs
        mock_para1 = MagicMock()
        mock_para1.text = "Test User"
        mock_para1.style.name = "Normal"

        mock_para2 = MagicMock()
        mock_para2.text = "Section Header"
        mock_para2.style.name = "Heading 1"

        mock_doc.paragraphs = [mock_para1, mock_para2]

        # Mock styles
        mock_style = MagicMock()
        mock_doc.styles = {'Normal': mock_style}

        mock_document_class.return_value = mock_doc

        with patch.object(Conversion, '_get_file_path', return_value=Path('/tmp/test.docx')):
            result = Conversion.page_formatting("test.docx", "Test User")

            assert result == True
            mock_doc.save.assert_called_once()

    @patch('app.utils.conversion.Document')
    def test_page_formatting_exception(self, mock_document_class):
        """Test page formatting handles exceptions."""
        mock_document_class.side_effect = Exception("File error")

        with patch.object(Conversion, '_get_file_path', return_value=Path('/tmp/test.docx')):
            result = Conversion.page_formatting("test.docx", "Test User")

            assert result == False


class TestConvertFileRouting:
    """Test suite for convert_file routing method."""
    user_id = Depends(get_current_user)

    @patch('subprocess.run')
    def test_convert_docx_to_md(self, mock_run):
        """Test routing DOCX to MD conversion."""
        mock_run.return_value = Mock(returncode=0)

        with patch('os.path.exists', return_value=True):
            result = Conversion.convert_file('docx', 'md', '/tmp/input.docx', '/tmp/output.md', user_id)

            assert result == True
            # Verify pandoc was called
            assert mock_run.called
            call_args = mock_run.call_args[0][0]
            assert 'pandoc' in call_args

    @patch('subprocess.run')
    def test_convert_odt_to_md(self, mock_run):
        """Test routing ODT to MD conversion."""
        mock_run.return_value = Mock(returncode=0)

        with patch('os.path.exists', return_value=True):
            result = Conversion.convert_file('odt', 'md', '/tmp/input.odt', '/tmp/output.md', user_id)

            assert result == True
            assert mock_run.called

    @patch('app.utils.conversion.MarkItDown')
    def test_convert_pdf_to_md(self, mock_markitdown_class):
        """Test routing PDF to MD conversion."""
        mock_md_instance = Mock()
        mock_result = Mock()
        mock_result.text_content = "# Content"
        mock_md_instance.convert.return_value = mock_result
        mock_markitdown_class.return_value = mock_md_instance

        mock_file = mock_open()
        with patch('builtins.open', mock_file):
            with patch('os.path.exists', return_value=True):
                result = Conversion.convert_file('pdf', 'md', '/tmp/input.pdf', '/tmp/output.md')

                assert result == True

    def test_convert_unsupported_to_md(self):
        """Test routing with unsupported source format to MD."""
        result = Conversion.convert_file('txt', 'md', '/tmp/input.txt', '/tmp/output.md')

        assert result == False


class TestHtmlConversions:
    """Test suite for HTML conversion methods."""

    @patch('builtins.open', new_callable=mock_open, read_data='<html><body>Test</body></html>')
    @patch('os.path.exists', return_value=True)
    @patch('os.makedirs')
    def test_html2docx_html4docx(self, mock_makedirs, mock_exists, mock_file):
        """Test HTML to DOCX conversion using html4docx."""
        with patch('app.utils.conversion.HtmlToDocx') as mock_html_to_docx:
            mock_parser = Mock()
            mock_doc = Mock()
            mock_parser.parse_html_string.return_value = mock_doc
            mock_html_to_docx.return_value = mock_parser

            result = Conversion.html2docx_html4docx('/tmp/input.html', '/tmp/output.docx')

            assert result == True
            mock_doc.save.assert_called_once()

    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open, read_data='<html>Test</html>')
    @patch('os.path.exists', return_value=True)
    @patch('os.makedirs')
    def test_html2odt_pandoc(self, mock_makedirs, mock_exists, mock_file, mock_run):
        """Test HTML to ODT conversion using pandoc."""
        mock_run.return_value = Mock(returncode=0)

        result = Conversion.html2odt_pandoc('/tmp/input.html', '/tmp/output.odt')

        assert result == True
        mock_run.assert_called_once()

    @patch('builtins.open', new_callable=mock_open, read_data='<html>Test</html>')
    @patch('os.path.exists', return_value=True)
    @patch('os.makedirs')
    @patch('app.utils.conversion.HTML')
    def test_html2pdf_weasyprint(self, mock_html_class, mock_makedirs, mock_exists, mock_file):
        """Test HTML to PDF conversion using WeasyPrint."""
        mock_html_instance = Mock()
        mock_html_class.return_value = mock_html_instance

        result = Conversion.html2pdf_weasyprint('/tmp/input.html', '/tmp/output.pdf')

        assert result == True
        mock_html_instance.write_pdf.assert_called_once()


class TestCleanHtmlForDocx:
    """Test suite for _clean_html_for_docx method."""

    def test_clean_html_removes_scripts(self):
        """Test that script tags are removed."""
        html = '<html><body><script>alert("test")</script><p>Content</p></body></html>'

        cleaned = Conversion._clean_html_for_docx(html)

        assert 'script' not in cleaned.lower()
        assert '<p>Content</p>' in cleaned

    def test_clean_html_removes_diff_tags(self):
        """Test that <ins> and <del> tags are handled."""
        html = '<html><body><p>Text <ins>added</ins> and <del>removed</del></p></body></html>'

        cleaned = Conversion._clean_html_for_docx(html)

        assert '<ins>' not in cleaned
        assert '<del>' not in cleaned
        assert 'added' in cleaned  # Content of <ins> should be kept

    def test_clean_html_preserves_structure(self):
        """Test that basic HTML structure is preserved."""
        html = '<body><h1>Title</h1><p>Paragraph</p></body>'

        cleaned = Conversion._clean_html_for_docx(html)

        assert '<!DOCTYPE html>' in cleaned
        assert '<html>' in html
        assert '<h1>Title</h1>' in cleaned
