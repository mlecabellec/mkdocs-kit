import os
import re
from urllib.parse import urlparse, unquote


def _strip_fenced_code_blocks(markdown_content):
    """Remove fenced code blocks (``` or ~~~) while preserving line alignment outside them."""
    lines = markdown_content.splitlines(keepends=True)
    filtered_lines = []
    in_fence = False
    fence_char = ""
    fence_len = 0
    for line in lines:
        stripped = line.lstrip()
        if not in_fence:
            fence_match = re.match(r'^(`{3,}|~{3,})(.*)$', stripped)
            if fence_match:
                marker = fence_match.group(1)
                rest = fence_match.group(2)
                if not (marker[0] == '`' and '`' in rest):
                    in_fence = True
                    fence_char = marker[0]
                    fence_len = len(marker)
                    continue
            filtered_lines.append(line)
        else:
            if stripped.startswith(fence_char * fence_len):
                trailing = stripped[fence_len:].strip()
                if trailing == "" or all(ch == fence_char for ch in trailing):
                    in_fence = False
                    continue
    return "".join(filtered_lines)


def check_links_in_markdown(markdown_content, page_file_path, docs_dir, reporter=None):
    """
    Scans markdown content for links and checks:
    1. If the link points to a directory (e.g. 'subfolder/' or resolving to a directory on disk)
       instead of an explicit file ('subfolder/index.md' or 'file.md').
    2. If the link points to a non-existent local file.
    """
    cleaned_markdown = _strip_fenced_code_blocks(markdown_content)

    # Scan left-to-right so standalone inline code spans (e.g. `[&](...)`) are skipped,
    # while markdown links whose label contains inline code (e.g. [`Foo`](foo.md)) are still checked.
    combined_pattern = re.compile(
        r'(?<!`)(?P<code_fence>`+)(?!`)(?:(?!\n\s*\n).)*?(?<!`)(?P=code_fence)(?!`)'
        r'|\[(?P<md_text>[^\]]+)\]\((?P<md_target>[^)]+)\)'
        r'|<a\b[^>]*href=["\'](?P<html_target>[^"\']+)["\'][^>]*>(?P<html_text>.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )

    links_found = []

    for match in combined_pattern.finditer(cleaned_markdown):
        if match.group('code_fence'):
            continue
        if match.group('md_target') is not None:
            text = match.group('md_text').strip()
            target = match.group('md_target').strip()
            links_found.append((text, target))
        elif match.group('html_target') is not None:
            target = match.group('html_target').strip()
            text = match.group('html_text').strip()
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

        # Strip anchor or query params and percent-decode path for disk resolution
        raw_path = unquote(parsed.path)
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
