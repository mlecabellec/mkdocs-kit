import os
import re
from urllib.parse import urlparse

def check_links_in_markdown(markdown_content, page_file_path, docs_dir, reporter=None):
    """
    Scans markdown content for links and checks:
    1. If the link points to a directory (e.g. 'subfolder/' or resolving to a directory on disk)
       instead of an explicit file ('subfolder/index.md' or 'file.md').
    2. If the link points to a non-existent local file.
    """
    # Regex for [text](url) and <a href="url">
    md_link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    html_link_pattern = r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>'

    links_found = []

    for match in re.finditer(md_link_pattern, markdown_content):
        text = match.group(1).strip()
        target = match.group(2).strip()
        links_found.append((text, target))

    for match in re.finditer(html_link_pattern, markdown_content, re.IGNORECASE):
        target = match.group(1).strip()
        text = match.group(2).strip()
        links_found.append((text, target))

    page_rel = os.path.relpath(page_file_path, docs_dir) if docs_dir else page_file_path
    page_dir = os.path.dirname(page_file_path)

    page_has_directory_link_warning = False

    for text, target in links_found:
        parsed = urlparse(target)
        if parsed.scheme in ('http', 'https', 'mailto', 'tel') or target.startswith('#'):
            if reporter:
                reporter.record_link(page_rel, target, text, "EXTERNAL", "External or anchor link")
            continue

        # Strip anchor or query params for path checking
        raw_path = parsed.path
        if not raw_path:
            continue

        # Check directory reference patterns
        is_directory_target = False
        warning_msg = ""

        # Case 1: URL path explicitly ends with trailing slash (e.g. "subfolder/" or "../subfolder/")
        if raw_path.endswith('/'):
            is_directory_target = True
            warning_msg = f"Link '{target}' has a trailing slash pointing to a directory listing instead of an index page."

        # Resolve local filesystem path
        if raw_path.startswith('/'):
            # Path relative to docs_dir
            resolved_disk_path = os.path.normpath(os.path.join(docs_dir, raw_path.lstrip('/')))
        else:
            # Path relative to page directory
            resolved_disk_path = os.path.normpath(os.path.join(page_dir, raw_path))

        # Case 2: Resolves to an actual directory on disk without an explicit file extension
        if not is_directory_target and os.path.isdir(resolved_disk_path):
            is_directory_target = True
            suggested = os.path.join(target, "index.md") if target else "index.md"
            warning_msg = f"Link '{target}' references directory '{resolved_disk_path}' instead of a target file (e.g. '{suggested}')."

        if is_directory_target:
            page_has_directory_link_warning = True
            if reporter:
                reporter.warn(f"Page '{page_rel}': Link '[{text}]({target})' points to a directory listing. {warning_msg}", category="LINK_DIRECTORY")
                reporter.record_link(page_rel, target, text, "WARNING_DIRECTORY", warning_msg)
        else:
            # Check if target exists on disk (if not anchor-only and not directory)
            # Try adding .md or /index.md if missing extension, but flag non-existent paths
            exists = os.path.exists(resolved_disk_path)
            if not exists and not os.path.splitext(resolved_disk_path)[1]:
                if os.path.exists(resolved_disk_path + ".md") or os.path.exists(os.path.join(resolved_disk_path, "index.md")):
                    exists = True

            if exists:
                if reporter:
                    reporter.record_link(page_rel, target, text, "VALID", "Target file resolved successfully")
            else:
                if reporter:
                    reporter.warn(f"Page '{page_rel}': Broken link '[{text}]({target})' (File '{resolved_disk_path}' not found)", category="LINK_BROKEN")
                    reporter.record_link(page_rel, target, text, "BROKEN", f"Target file '{resolved_disk_path}' missing")

    return page_has_directory_link_warning
