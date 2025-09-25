import json
import os
import re
import requests
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

def sanitize_filename(name):
    """
    Sanitizes a string to be used as a valid filename.
    """
    if not name:
        return ""
    name = name.strip().replace(" ", "_")
    return re.sub(r'(?u)[^-\w.]', '', name)

def make_session(retries=3, backoff=0.3):
    """Creates a requests Session with automatic retries for network robustness."""
    s = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff,
        status_forcelist=(500, 502, 503, 504)
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({"User-Agent": "Mozilla/5.0 (compatible; TUF-Downloader/1.0)"})
    return s

def download_article_worker(post_link, session):
    """
    Worker function to download and save a single article.
    Returns a status message.
    """
    if not post_link:
        return "Skipped: Empty post link."

    try:
        path = urlparse(post_link).path.strip('/')
        path_parts = path.split('/')

        if len(path_parts) < 1:
            return f"Skipped: Could not determine category for {post_link}"

        category = sanitize_filename(path_parts[0])
        slug = sanitize_filename(path_parts[-1])

        if not slug:
            return f"Skipped: Could not determine slug for {post_link}"

        dir_path = os.path.join("articles", category)
        os.makedirs(dir_path, exist_ok=True)

        filename = os.path.join(dir_path, f"{slug}.json")

        if os.path.exists(filename):
            return f"Exists: {filename}"

        api_url = f"https://backend.takeuforward.org/api/blog/article/{path}"
        response = session.get(api_url, timeout=20)
        response.raise_for_status()

        with open(filename, "w", encoding="utf-8") as outfile:
            json.dump(response.json(), outfile, indent=4)

        return f"Success: Saved to {filename}"

    except requests.exceptions.RequestException as e:
        return f"Error (Request): Failed {post_link} with error: {e}"
    except Exception as e:
        return f"Error (General): Failed {post_link} with error: {e}"

def download_all_articles_parallel(max_workers=10):
    """
    Finds all article links in a2z.json and downloads them in parallel.
    """
    try:
        with open("a2z.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading a2z.json: {e}")
        return

    # --- Step 1: Collect all post links ---
    all_links = []
    for step in data:
        for sub_step in step.get("sub_steps", []):
            for topic in sub_step.get("topics", []):
                if post_link := topic.get("post_link"):
                    all_links.append(post_link)

    if not all_links:
        print("No article links found in a2z.json.")
        return

    print(f"Found {len(all_links)} unique articles to process.")

    # --- Step 2: Download in parallel with a progress bar ---
    session = make_session()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks to the executor
        future_to_link = {executor.submit(download_article_worker, link, session): link for link in all_links}

        # Process results as they complete, with a tqdm progress bar
        for future in tqdm(as_completed(future_to_link), total=len(all_links), desc="Downloading Articles"):
            link = future_to_link[future]
            try:
                result = future.result()
                if "Error" in result:
                    tqdm.write(result) # Print errors to the console
            except Exception as exc:
                tqdm.write(f"Article '{link}' generated an exception: {exc}")


if __name__ == "__main__":
    # Ensure you have 'tqdm' installed: pip install requests tqdm
    download_all_articles_parallel(max_workers=15)
    print("\nAll downloads complete.")
