# Copilot Instructions for A2Z DSA Sheet

This repository manages the content for a Data Structures and Algorithms (DSA) learning platform. It uses a JSON-based storage system and Python scripts to render static HTML articles.

## 🏗 Architecture & Data Flow

- **Master Curriculum (`a2z.json`):** The central source of truth for the course structure. It defines steps, sub-steps, and topics, linking to external resources (YouTube, LeetCode, etc.).
- **Content Storage (`a2z_old_sheet_articles/articles/`):** Contains individual problem articles in JSON format.
  - Organized by topic folders (e.g., `arrays/`, `binary-search/`).
  - Each JSON file contains metadata (`title`, `slug`) and a `content` field with raw HTML.
- **Rendering Engine (`a2z_old_sheet_articles/render_article.py`):** Converts Article JSONs into standalone HTML files using `template.html`.

## 🛠 Critical Workflows

### 1. Rendering Articles
To generate HTML files from the JSON sources, run the rendering script from the root:
```bash
python a2z_old_sheet_articles/render_article.py
```
This will traverse `articles/` and generate corresponding `.html` files.

### 2. Content Editing
- **Do not edit generated HTML files directly.** Always modify the source JSON files in `a2z_old_sheet_articles/articles/`.
- The `content` field in JSON is a string containing HTML. Be careful with escaping quotes.

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
- **`scripts/download_json.py`**: Fetches article data from remote URLs.
- **`scripts/clean_trackers.py`**: Utility to clean up tracking parameters or artifacts.
- **Dependencies**: Standard Python libraries (`json`, `os`, `re`) + `requests` and `tqdm` for network scripts.
