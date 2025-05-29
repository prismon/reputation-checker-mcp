"""Link extraction utilities."""

import re
from typing import List, Set
from urllib.parse import urljoin, urlparse

import validators
from bs4 import BeautifulSoup


class LinkExtractor:
    """Extract links from HTML or text content."""

    # Common URL patterns
    URL_PATTERN = re.compile(
        r"https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}"
        r"\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)",
        re.IGNORECASE,
    )

    # Markdown link pattern
    MARKDOWN_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)", re.IGNORECASE)

    def extract_links(
        self, content: str, content_type: str = "auto", base_url: str = None
    ) -> List[str]:
        """
        Extract all links from content.

        Args:
            content: The content to extract links from
            content_type: "html", "text", or "auto" (auto-detect)
            base_url: Base URL for resolving relative links

        Returns:
            List of unique URLs found in the content
        """
        if content_type == "auto":
            content_type = self._detect_content_type(content)

        links: Set[str] = set()

        if content_type == "html":
            links.update(self._extract_html_links(content, base_url))

        # Always extract plain text URLs as well
        links.update(self._extract_text_links(content))

        # Filter and validate links
        valid_links = []
        for link in links:
            if self._is_valid_link(link):
                valid_links.append(link)

        return sorted(list(set(valid_links)))

    def _detect_content_type(self, content: str) -> str:
        """Auto-detect content type."""
        # Simple heuristic: if it contains HTML tags, treat as HTML
        if (
            "<html" in content.lower()
            or "<body" in content.lower()
            or "<a href" in content.lower()
        ):
            return "html"
        return "text"

    def _extract_html_links(self, html_content: str, base_url: str = None) -> Set[str]:
        """Extract links from HTML content."""
        links = set()

        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Extract from <a> tags
            for tag in soup.find_all("a", href=True):
                href = tag["href"]
                if base_url:
                    href = urljoin(base_url, href)
                links.add(href)

            # Extract from <link> tags (stylesheets, etc.)
            for tag in soup.find_all("link", href=True):
                href = tag["href"]
                if base_url:
                    href = urljoin(base_url, href)
                links.add(href)

            # Extract from <img> tags
            for tag in soup.find_all("img", src=True):
                src = tag["src"]
                if base_url:
                    src = urljoin(base_url, src)
                links.add(src)

            # Extract from <script> tags
            for tag in soup.find_all("script", src=True):
                src = tag["src"]
                if base_url:
                    src = urljoin(base_url, src)
                links.add(src)

            # Extract from meta refresh
            for tag in soup.find_all("meta", attrs={"http-equiv": "refresh"}):
                content = tag.get("content", "")
                match = re.search(r"url=([^;]+)", content, re.IGNORECASE)
                if match:
                    url = match.group(1).strip("\"'")
                    if base_url:
                        url = urljoin(base_url, url)
                    links.add(url)

        except Exception:
            # If parsing fails, fall back to regex extraction
            pass

        return links

    def _extract_text_links(self, text_content: str) -> Set[str]:
        """Extract links from plain text using regex."""
        links = set()

        # Extract standard URLs
        for match in self.URL_PATTERN.finditer(text_content):
            links.add(match.group(0))

        # Extract Markdown links
        for match in self.MARKDOWN_PATTERN.finditer(text_content):
            url = match.group(2)
            if url.startswith("http://") or url.startswith("https://"):
                links.add(url)

        # Extract URLs in quotes or parentheses
        quoted_url_pattern = re.compile(
            r'["\']?(https?://[^"\'\s<>]+)["\']?', re.IGNORECASE
        )
        for match in quoted_url_pattern.finditer(text_content):
            links.add(match.group(1))

        return links

    def _is_valid_link(self, url: str) -> bool:
        """Check if a URL is valid and should be included."""
        if not url:
            return False

        # Skip common non-HTTP protocols
        skip_protocols = [
            "javascript:",
            "mailto:",
            "tel:",
            "ftp:",
            "file:",
            "data:",
            "about:",
            "chrome:",
            "edge:",
        ]

        url_lower = url.lower()
        for protocol in skip_protocols:
            if url_lower.startswith(protocol):
                return False

        # Skip anchors
        if url.startswith("#"):
            return False

        # Validate URL format
        if url.startswith("http://") or url.startswith("https://"):
            return validators.url(url) is True

        return False

    def extract_domains(self, urls: List[str]) -> List[str]:
        """Extract unique domains from a list of URLs."""
        domains = set()

        for url in urls:
            try:
                parsed = urlparse(url)
                if parsed.hostname:
                    domains.add(parsed.hostname.lower())
            except Exception:
                continue

        return sorted(list(domains))
