# A2Z DSA SHEET

A Data Structures and Algorithms (DSA) learning platform with JSON-based content storage and Python-powered static site generation.

> **Disclaimer:** For educational purposes only

## 📁 Project Structure

```
a2z_old_sheet/
├── a2z.json                 # Master curriculum - source of truth
├── index.html               # Main entry point
├── content/                 # Source content (edit these)
│   └── articles/            # Article JSON files by topic
│       ├── arrays/
│       ├── binary-search/
│       ├── binary-tree/
│       ├── dynamic-programming/
│       ├── graph/
│       ├── linked-list/
│       └── ...
├── public/                  # Generated output (do not edit)
│   ├── index.html
│   ├── assets/              # Static assets (logos, images)
│   └── articles/            # Generated HTML articles
├── src/                     # Python scripts
│   ├── render_article.py    # JSON → HTML renderer
│   ├── download_json.py     # Article downloader
│   ├── localize_assets.py   # Asset localizer
│   ├── clean_trackers.py    # URL tracker cleaner
│   └── debitlify.py         # Bit.ly link expander
├── templates/               # HTML templates
│   └── template.html        # Article template
└── docs/                    # Documentation
```

## 🚀 Quick Start

### Install Dependencies

```bash
pip install requests tqdm beautifulsoup4
```

### Typical Workflow

```bash
# 1. Download latest articles from API
python src/download_json.py

# 2. Render JSON to HTML
python src/render_article.py

# 3. View the result
open public/articles/index.html
```

## 📚 Script Usage

### 1. Render Articles (JSON → HTML)

```bash
# Default: reads from content/articles/, outputs to public/articles/
python src/render_article.py

# Custom paths
python src/render_article.py -c /path/to/content -o /path/to/output

# Skip asset localization (faster, for testing)
python src/render_article.py --skip-localize

# See all options
python src/render_article.py --help
```

### 2. Download Articles from API

```bash
# Default: downloads to content/articles/
python src/download_json.py

# Custom output directory
python src/download_json.py -o /path/to/output

# Adjust parallel workers (default: 15)
python src/download_json.py -w 20

# See all options
python src/download_json.py --help
```

### 3. Clean URL Trackers

```bash
# Remove tracking params (utm_source, fbclid, etc.) from URLs
python src/clean_trackers.py a2z.json
# Creates: a2z_cleaned.json
```

### 4. Expand Bit.ly Links

```bash
# Expand shortened URLs to their destinations
python src/debitlify.py a2z.json
# Creates: a2z_expanded.json
```

### 5. Localize Assets

```bash
# Download remote images/assets locally (usually called by render_article.py)
python src/localize_assets.py public/articles/ -v
```

## 📝 Content Editing

**Important:** Always edit source JSON files in `content/articles/`, never the generated HTML in `public/`.

### Article JSON Format

```json
{
  "title": "Problem Title",
  "slug": "problem-slug",
  "content": "<!-- wp:paragraph -->...HTML Content...<!-- /wp:paragraph -->",
  "topics": [{"topic-id": "arrays", "topic-title": "Arrays"}]
}
```
