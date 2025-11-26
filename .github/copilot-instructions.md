# Copilot Instructions for A2Z DSA Sheet

This repository manages the content for a Data Structures and Algorithms (DSA) learning platform. It uses a JSON-based storage system and Python scripts to render static HTML articles.

## 🏗 Architecture & Data Flow

```
a2z/
├── a2z.json              # Master curriculum - source of truth
├── content/articles/     # Source JSON files (EDIT THESE)
├── public/articles/      # Generated HTML (DO NOT EDIT)
├── src/                  # Python scripts
│   ├── render_article.py
│   ├── download_json.py
│   ├── localize_assets.py
│   ├── clean_trackers.py
│   └── debitlify.py
└── templates/            # HTML templates
```

- **Master Curriculum (`a2z.json`):** The central source of truth for the course structure. It defines steps, sub-steps, and topics, linking to external resources (YouTube, LeetCode, etc.).
- **Content Storage (`content/articles/`):** Contains individual problem articles in JSON format.
  - Organized by topic folders (e.g., `arrays/`, `binary-search/`).
  - Each JSON file contains metadata (`title`, `slug`) and a `content` field with raw HTML.
- **Rendering Engine (`src/render_article.py`):** Converts Article JSONs into standalone HTML files using `templates/template.html`.
- **Output Directory (`public/`):** Contains all generated HTML files and static assets.

## 🛠 Critical Workflows

### 1. Rendering Articles

To generate HTML files from the JSON sources, run:

```bash
python src/render_article.py
```

This reads from `content/articles/` and outputs to `public/articles/`.

Options:
- `-c, --content-dir`: Custom content directory
- `-o, --output-dir`: Custom output directory  
- `-t, --template`: Custom template file
- `--skip-localize`: Skip asset localization step

### 2. Content Editing

- **Do not edit generated HTML files directly.** Always modify the source JSON files in `content/articles/`.
- The `content` field in JSON is a string containing HTML. Be careful with escaping quotes.

### 3. Downloading Articles

```bash
python src/download_json.py
```

Downloads articles from TakeUForward API to `content/articles/`.

## 📝 Content Conventions

### Article JSON Structure

```json
{
  "title": "Problem Title",
  "slug": "problem-slug",
  "content": "<!-- wp:paragraph -->...HTML Content...<!-- /wp:paragraph -->",
  "topics": [{"topic-id": "arrays", "topic-title": "Arrays"}]
}
```

### Code Block Pattern

The project uses a specific tabbed interface for code solutions (C++, Java, Python, JS). When adding/editing code, maintain this HTML structure inside the JSON `content` string:

```html
<div class="code-section secondary-details">
  <div class="code-tabs">
    <button class="code-tab dsa_article_code_active" data-lang="cpp">C++</button>
    <!-- ... other buttons ... -->
  </div>
  <div class="code-content">
    <div class="code-block dsa_article_code_active" data-lang="cpp">
      <pre class="wp-block-code"><code lang="cpp" class="language-cpp">
        // C++ Code Here
      </code></pre>
    </div>
    <!-- ... other code blocks ... -->
  </div>
</div>
```

### HTML Markers

- Use `<!-- wp:paragraph -->` and `<!-- /wp:paragraph -->` to wrap text blocks.
- Use `<!-- Insert ... Here -->` comments as guideposts for where specific content sections (Examples, Approaches, Code) should go.

## 🐍 Python Scripts

All scripts are in `src/` directory:

| Script | Purpose |
|--------|---------|
| `render_article.py` | JSON → HTML conversion |
| `download_json.py` | Fetch articles from API |
| `localize_assets.py` | Download remote assets locally |
| `clean_trackers.py` | Remove URL tracking parameters |
| `debitlify.py` | Expand shortened URLs |

**Dependencies:** `requests`, `tqdm`, `beautifulsoup4`
