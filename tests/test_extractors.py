"""Unit tests for extractors.py"""

import pytest
from url_reputation_checker.extractors import LinkExtractor


class TestLinkExtractor:
    """Test suite for LinkExtractor."""

    @pytest.fixture
    def extractor(self):
        """Create a LinkExtractor instance."""
        return LinkExtractor()

    def test_extract_links_html_basic(self, extractor):
        """Test basic HTML link extraction."""
        html = """
        <html>
        <body>
            <a href="https://example.com">Example</a>
            <a href="https://test.com">Test</a>
        </body>
        </html>
        """
        
        links = extractor.extract_links(html, content_type="html")
        
        assert len(links) == 2
        assert "https://example.com" in links
        assert "https://test.com" in links

    def test_extract_links_html_various_elements(self, extractor):
        """Test extraction from various HTML elements."""
        html = """
        <html>
        <head>
            <link rel="stylesheet" href="https://example.com/style.css">
            <script src="https://example.com/script.js"></script>
            <meta http-equiv="refresh" content="0; url=https://example.com/redirect">
        </head>
        <body>
            <a href="https://example.com/page">Link</a>
            <img src="https://example.com/photo.jpg" alt="Photo">
        </body>
        </html>
        """
        
        links = extractor.extract_links(html, content_type="html")
        
        expected_links = {
            "https://example.com/style.css",
            "https://example.com/script.js",
            "https://example.com/redirect",
            "https://example.com/page",
            "https://example.com/photo.jpg"
        }
        
        assert set(links) == expected_links

    def test_extract_links_html_with_base_url(self, extractor):
        """Test HTML link extraction with base URL."""
        html = """
        <html>
        <body>
            <a href="/page">Relative</a>
            <a href="page.html">Same level</a>
            <a href="https://example.com">Absolute</a>
        </body>
        </html>
        """
        
        links = extractor.extract_links(html, content_type="html", base_url="https://base.com/")
        
        assert "https://base.com/page" in links
        assert "https://base.com/page.html" in links
        assert "https://example.com" in links

    def test_extract_links_text_basic(self, extractor):
        """Test basic text link extraction."""
        text = """
        Check out https://example.com for more info.
        Also visit http://test.com
        """
        
        links = extractor.extract_links(text, content_type="text")
        
        assert len(links) == 2
        assert "https://example.com" in links
        assert "http://test.com" in links

    def test_extract_links_text_markdown(self, extractor):
        """Test extraction from Markdown formatted text."""
        text = """
        Here's a [link to example](https://example.com).
        Another [test link](http://test.com "Test Title").
        """
        
        links = extractor.extract_links(text, content_type="text")
        
        assert "https://example.com" in links
        assert "http://test.com" in links

    def test_extract_links_text_quoted(self, extractor):
        """Test extraction of quoted URLs."""
        text = """
        The URL is "https://example.com"
        Another one: 'http://test.com'
        """
        
        links = extractor.extract_links(text, content_type="text")
        
        assert "https://example.com" in links
        assert "http://test.com" in links

    def test_extract_links_auto_detect_html(self, extractor):
        """Test auto-detection of HTML content."""
        html = """
        <html>
        <body>
            <a href="https://example.com">Example</a>
        </body>
        </html>
        """
        
        # Should auto-detect as HTML
        links = extractor.extract_links(html)  # content_type="auto" by default
        
        assert "https://example.com" in links

    def test_extract_links_auto_detect_text(self, extractor):
        """Test auto-detection of text content."""
        text = "Just plain text with https://example.com"
        
        # Should auto-detect as text
        links = extractor.extract_links(text)
        
        assert "https://example.com" in links

    def test_extract_links_duplicate_removal(self, extractor):
        """Test that duplicate links are removed."""
        html = """
        <a href="https://example.com">Link 1</a>
        <a href="https://example.com">Link 2</a>
        Text with https://example.com again
        """
        
        links = extractor.extract_links(html)
        
        # Should only have one instance
        assert links.count("https://example.com") == 1

    def test_extract_links_invalid_urls_filtered(self, extractor):
        """Test that invalid URLs are filtered out."""
        html = """
        <a href="">Empty</a>
        <a href="javascript:void(0)">JavaScript</a>
        <a href="mailto:test@example.com">Email</a>
        <a href="tel:+1234567890">Phone</a>
        <a href="#anchor">Anchor</a>
        <a href="https://example.com">Valid</a>
        """
        
        links = extractor.extract_links(html, content_type="html")
        
        # Only valid HTTP(S) URLs should be extracted
        assert len(links) == 1
        assert "https://example.com" in links

    def test_extract_links_meta_refresh(self, extractor):
        """Test extraction from meta refresh tags."""
        html = """
        <html>
        <head>
            <meta http-equiv="refresh" content="0; url=https://example.com/redirect">
            <meta http-equiv="refresh" content="5;url='https://test.com'">
        </head>
        </html>
        """
        
        links = extractor.extract_links(html, content_type="html")
        
        assert "https://example.com/redirect" in links
        assert "https://test.com" in links

    def test_extract_links_malformed_html(self, extractor):
        """Test extraction from malformed HTML."""
        html = """
        <html>
        <body>
            <a href="https://example.com">Valid link
            <a href="https://test.com"
        """
        
        links = extractor.extract_links(html, content_type="html")
        
        # Should still extract valid links despite malformed HTML
        assert "https://example.com" in links

    def test_detect_content_type_html(self, extractor):
        """Test content type detection for HTML."""
        assert extractor._detect_content_type("<html>content</html>") == "html"
        assert extractor._detect_content_type("<body>content</body>") == "html"
        assert extractor._detect_content_type('<a href="test">link</a>') == "html"

    def test_detect_content_type_text(self, extractor):
        """Test content type detection for text."""
        assert extractor._detect_content_type("Just plain text") == "text"
        assert extractor._detect_content_type("No HTML tags here") == "text"

    def test_is_valid_link(self, extractor):
        """Test link validation."""
        # Valid links
        assert extractor._is_valid_link("https://example.com") is True
        assert extractor._is_valid_link("http://test.com") is True
        
        # Invalid links
        assert extractor._is_valid_link("") is False
        assert extractor._is_valid_link("javascript:void(0)") is False
        assert extractor._is_valid_link("mailto:test@example.com") is False
        assert extractor._is_valid_link("#anchor") is False
        assert extractor._is_valid_link("ftp://example.com") is False

    def test_extract_domains(self, extractor):
        """Test domain extraction from URLs."""
        urls = [
            "https://example.com/page",
            "https://subdomain.example.com/other",
            "http://test.com:8080/path",
            "https://another.org"
        ]
        
        domains = extractor.extract_domains(urls)
        
        expected_domains = ["another.org", "example.com", "subdomain.example.com", "test.com"]
        assert domains == expected_domains  # Should be sorted

    def test_extract_domains_duplicates(self, extractor):
        """Test domain extraction with duplicate URLs."""
        urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://EXAMPLE.COM/page3",  # Different case
            "https://test.com"
        ]
        
        domains = extractor.extract_domains(urls)
        
        assert domains == ["example.com", "test.com"]

    def test_extract_domains_invalid_urls(self, extractor):
        """Test domain extraction with invalid URLs."""
        urls = [
            "https://example.com",
            "not-a-url",
            "http://",
            "https://test.com"
        ]
        
        domains = extractor.extract_domains(urls)
        
        # Should only extract valid domains
        assert domains == ["example.com", "test.com"]

    def test_extract_links_sorted_output(self, extractor):
        """Test that output links are sorted."""
        html = """
        <a href="https://zebra.com">Z</a>
        <a href="https://apple.com">A</a>
        <a href="https://banana.com">B</a>
        """
        
        links = extractor.extract_links(html, content_type="html")
        
        assert links == ["https://apple.com", "https://banana.com", "https://zebra.com"]

    def test_extract_links_complex_urls(self, extractor):
        """Test extraction of complex URLs."""
        text = """
        https://example.com/path?query=value&other=123
        https://test.com:8080/api/v1/users
        https://subdomain.example.org/path/to/page#section
        """
        
        links = extractor.extract_links(text, content_type="text")
        
        assert "https://example.com/path?query=value&other=123" in links
        assert "https://test.com:8080/api/v1/users" in links
        assert "https://subdomain.example.org/path/to/page#section" in links

    def test_extract_links_url_pattern_regex(self, extractor):
        """Test the URL pattern regex."""
        # This tests the actual regex pattern used
        pattern = extractor.URL_PATTERN
        
        # Should match
        assert pattern.search("https://example.com") is not None
        assert pattern.search("http://test.co.uk") is not None
        assert pattern.search("https://sub.domain.com/path") is not None
        
        # Should not match incomplete URLs
        assert pattern.search("https://") is None
        assert pattern.search("example.com") is None  # No protocol

    def test_extract_links_markdown_pattern_regex(self, extractor):
        """Test the Markdown pattern regex."""
        pattern = extractor.MARKDOWN_PATTERN
        
        # Should match
        assert pattern.search("[text](https://example.com)") is not None
        assert pattern.search("[link text](http://test.com)") is not None
        
        # Should not match
        assert pattern.search("[text]") is None
        assert pattern.search("(url)") is None