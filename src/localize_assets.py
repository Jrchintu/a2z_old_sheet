#!/usr/bin/env python3
"""
localize_assets.py

Usage:
    python localize_assets.py /path/to/html_root

Downloads and localizes all remote assets (images, CSS backgrounds) referenced
in HTML files. It creates an "assets" folder next to each HTML file.

This version uses content hashing for the cache to avoid storing duplicate
files, even if they come from different URLs.

Installs:
    pip install requests beautifulsoup4
"""

import os
import re
import sys
import shutil
import argparse
import logging
import json
import hashlib
from pathlib import Path
from urllib.parse import urlparse, unquote
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed

LOG = logging.getLogger("localize_assets")

# --- helpers ---------------------------------------------------------------
def sanitize_filename(name: str) -> str:
    """Removes unsafe characters from a filename."""
    name = unquote(name or "")
    name = name.split("?")[0].split("#")[0]
    name = re.sub(r'[^A-Za-z0-9._-]', '_', name)
    return name or "file"

def parse_srcset(srcset: str):
    """Parses an srcset attribute into a list of (url, descriptor) tuples."""
    if not srcset: return []
    return [(parts[0], " ".join(parts[1:])) for p in srcset.split(",") if (parts := p.strip().split())]

def build_srcset(parts):
    """Builds an srcset string from a list of (url, descriptor) tuples."""
    return ", ".join([f"{u} {d}".strip() for u, d in parts])

def find_css_urls(text: str):
    """Finds all url(...) values in a block of CSS."""
    if not text: return []
    return [m.group(2) for m in re.finditer(r'url\(\s*([\'"]?)(.*?)\1\s*\)', text, flags=re.IGNORECASE)]

def safe_makedir(p: Path):
    """Creates a directory if it doesn't exist."""
    p.mkdir(parents=True, exist_ok=True)

def get_file_hash(path: Path) -> str:
    """Calculates the sha256 hash of a file's content."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def _get_asset_nodes(soup):
    """Generator function to find and yield all nodes that might contain asset URLs."""
    # Images and sources, including common lazy-loading attributes
    for tag in soup.find_all(['img', 'source']):
        for attr in ['src', 'srcset', 'data-src', 'data-original']:
            if tag.has_attr(attr):
                yield tag, attr

    # Linked stylesheets
    for tag in soup.find_all('link', rel='stylesheet', href=True):
        yield tag, 'href'

    # Inline styles on any tag
    for tag in soup.find_all(style=True):
        if tag['style']:
            yield tag, 'style'

    # <style> blocks
    for tag in soup.find_all('style'):
        if tag.string:
            yield tag, 'style_block'

# --- downloader ------------------------------------------------------------
def make_session(retries=3, backoff=0.3):
    """Creates a requests Session with automatic retries."""
    s = requests.Session()
    retry = Retry(total=retries, backoff_factor=backoff, status_forcelist=(429, 500, 502, 503, 504))
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    s.headers.update({"User-Agent": "Mozilla/5.0 (compatible; asset-downloader/1.0)"})
    return s

def download_to_file(session: requests.Session, url: str, dest: Path, verify_ssl=True, max_mb=100):
    """Downloads a URL to a specific destination file path."""
    tmp = dest.with_suffix(dest.suffix + ".part")
    safe_makedir(dest.parent)
    try:
        with session.get(url, stream=True, timeout=30, verify=verify_ssl) as r:
            r.raise_for_status()
            max_bytes = max_mb * 1024 * 1024
            with open(tmp, "wb") as fh:
                size = 0
                for chunk in r.iter_content(chunk_size=8192):
                    size += len(chunk)
                    if size > max_bytes:
                        raise RuntimeError(f"File exceeded max size of {max_mb} MB")
                    fh.write(chunk)
            tmp.rename(dest)
        return True, None
    except Exception as e:
        if tmp.exists():
            try: tmp.unlink()
            except OSError: pass
        return False, str(e)

def save_cache_index(path: Path, data: dict):
    """Atomically saves the cache index to prevent corruption."""
    try:
        temp_path = path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        shutil.move(str(temp_path), str(path))
    except IOError as e:
        LOG.error("Could not save cache index: %s", e)

def discover_urls_in_html(html_path: Path):
    """Finds all remote asset URLs in a single HTML file."""
    urls = set()
    try:
        soup = BeautifulSoup(html_path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    except Exception as e:
        LOG.error("Could not read or parse %s: %s", html_path, e)
        return urls

    def add_if_remote(raw_url):
        raw_url = (raw_url or "").strip()
        if not raw_url or raw_url.lower().startswith("data:"): return
        url = "https:" + raw_url if raw_url.startswith("//") else raw_url
        if urlparse(url).scheme in ("http", "https"):
            urls.add(url)

    for node, attr in _get_asset_nodes(soup):
        if attr == 'srcset':
            for url, _ in parse_srcset(node[attr]): add_if_remote(url)
        elif attr in ['style', 'style_block']:
            content = node[attr] if attr == 'style' else node.string
            for url in find_css_urls(content): add_if_remote(url)
        else:
            add_if_remote(node[attr])
    return urls

def download_worker(session, url, cache_dir, verify_ssl, dry_run):
    """Downloads a single URL and saves it to the cache using a content hash."""
    path_part = urlparse(url).path
    fname_base = sanitize_filename(os.path.basename(path_part))
    _, ext = os.path.splitext(fname_base)

    temp_download_path = cache_dir / f"temp_{hashlib.sha256(url.encode()).hexdigest()}{ext}"

    if dry_run:
        return url, f"dry_run_hash_for_{fname_base}{ext}"

    LOG.info("Downloading: %s", url)
    ok, err = download_to_file(session, url, temp_download_path, verify_ssl=verify_ssl)
    if not ok:
        LOG.warning(" -> FAILED to download %s: %s", url, err)
        return url, None

    try:
        content_hash = get_file_hash(temp_download_path)
        final_cache_fname = f"{content_hash[:32]}{ext}"
        final_cache_path = cache_dir / final_cache_fname

        if final_cache_path.exists():
            temp_download_path.unlink()
            LOG.info(" -> Content hash exists. Discarding duplicate.")
        else:
            temp_download_path.rename(final_cache_path)
            LOG.info(" -> New content, caching as %s", final_cache_fname)
        return url, final_cache_fname
    except Exception as e:
        LOG.error(" -> FAILED processing downloaded file for %s: %s", url, e)
        if temp_download_path.exists(): temp_download_path.unlink()
        return url, None

def rewrite_html_file(html_path: Path, assets_dirname, url_cache, cache_dir, dry_run):
    """Rewrites a single HTML file to point to cached/local assets."""
    LOG.info("Rewriting HTML: %s", html_path)
    try:
        text = html_path.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(text, "html.parser")
    except Exception as e:
        LOG.error("Could not read or parse %s: %s", html_path, e)
        return

    assets_dir = html_path.parent / assets_dirname
    safe_makedir(assets_dir)

    def handle_url(raw_url):
        raw_url = (raw_url or "").strip()
        if not raw_url or raw_url.lower().startswith("data:"): return None

        url_to_check = "https:" + raw_url if raw_url.startswith("//") else raw_url

        if urlparse(url_to_check).scheme in ("http", "https"): # Remote URL
            cached_fname = url_cache.get(url_to_check)
            if not cached_fname:
                LOG.warning("URL %s not in cache map (download may have failed).", url_to_check)
                return None
            cached_asset = cache_dir / cached_fname
            if not cached_asset.is_file():
                LOG.warning("Asset for %s not found in cache at %s", url_to_check, cached_asset)
                return None

            # The cached_fname is already deterministic (hash-based). Use it directly.
            final_name = cached_fname
            dest_path = assets_dir / final_name

            # Copy from cache to local assets dir only if it's not already there.
            if not dry_run and not dest_path.exists():
                shutil.copy2(cached_asset, dest_path)

            return final_name
        else: # Local URL
            return None # This script focuses on remote assets

    for node, attr in _get_asset_nodes(soup):
        if attr == 'srcset':
            parts = parse_srcset(node[attr])
            new_parts = []
            for u, d in parts:
                new_path = handle_url(u)
                new_parts.append((f"{assets_dirname}/{new_path}", d) if new_path else (u, d))
            node[attr] = build_srcset(new_parts)
        elif attr in ['style', 'style_block']:
            content = node[attr] if attr == 'style' else node.string
            for u in find_css_urls(content):
                new_path = handle_url(u)
                if new_path: content = content.replace(u, f"{assets_dirname}/{new_path}")

            if attr == 'style': node[attr] = content
            else: node.string = content
        else:
            if new_path := handle_url(node[attr]):
                node[attr] = f"{assets_dirname}/{new_path}"

    if not dry_run:
        html_path.write_text(str(soup), encoding="utf-8")
        LOG.info("Saved updated HTML: %s", html_path)

def main_process(root_dir: Path, assets_dirname: str, max_workers: int, clear_cache: bool, verify_ssl: bool, dry_run: bool):
    """Main logic for asset localization."""
    cache_dir = root_dir / ".asset_cache"
    if clear_cache and cache_dir.exists():
        LOG.info("Clearing cache at %s", cache_dir)
        shutil.rmtree(cache_dir)
    safe_makedir(cache_dir)

    cache_index_path = cache_dir / "index.json"
    url_cache = {}
    if cache_index_path.is_file():
        try:
            url_cache = json.loads(cache_index_path.read_text(encoding="utf-8"))
            LOG.info("Loaded %d items from cache index.", len(url_cache))
        except (json.JSONDecodeError, IOError) as e:
            LOG.warning("Could not load cache index: %s. Starting fresh.", e)

    html_files = list(root_dir.rglob("*.html"))
    if not html_files:
        LOG.warning("No .html files found in %s. Nothing to do.", root_dir)
        return

    # Phase 1: Discover all unique URLs
    LOG.info("Discovering URLs in %d HTML files...", len(html_files))
    all_urls = set().union(*(discover_urls_in_html(p) for p in html_files))
    urls_to_download = all_urls - url_cache.keys()
    LOG.info("Found %d unique remote assets. %d need to be downloaded.", len(all_urls), len(urls_to_download))

    # Phase 2: Download new assets in parallel
    if urls_to_download:
        session = make_session()
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(download_worker, session, url, cache_dir, verify_ssl, dry_run) for url in urls_to_download]
            for future in as_completed(futures):
                try:
                    res_url, cache_name = future.result()
                    if cache_name:
                        url_cache[res_url] = cache_name
                        if not dry_run: save_cache_index(cache_index_path, url_cache)
                except Exception as exc:
                    LOG.error('A download worker generated an exception: %s', exc)

    # Phase 3: Rewrite all HTML files
    LOG.info("All downloads complete. Rewriting HTML files...")
    for p in html_files:
        rewrite_html_file(p, assets_dirname, url_cache, cache_dir, dry_run)

# --- CLI -------------------------------------------------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Download/localize assets referenced in local HTML files.")
    ap.add_argument("root", help="Root folder to scan for HTML files")
    ap.add_argument("--assets-name", default="assets", help="Name of assets subfolder (default: assets)")
    ap.add_argument("--workers", type=int, default=10, help="Number of parallel download workers (default: 10)")
    ap.add_argument("--dry-run", action="store_true", help="Do not write files; only print actions")
    ap.add_argument("--no-verify-ssl", action="store_true", help="Do not verify SSL certificates")
    ap.add_argument("--clear-cache", action="store_true", help="Delete the asset cache before running")
    ap.add_argument("--verbose", "-v", action="store_true", help="Verbose debug output")
    args = ap.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s: %(message)s")

    root = Path(args.root)
    if not root.is_dir():
        LOG.error("Root path does not exist or is not a directory: %s", root)
        sys.exit(1)

    main_process(root, args.assets_name, args.workers, args.clear_cache, not args.no_verify_ssl, args.dry_run)

