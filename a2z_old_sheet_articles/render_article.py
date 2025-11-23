import json
import sys
import os
import subprocess
import re
from pathlib import Path

def read_template(template_path='template.html'):
    """Reads the HTML template file."""
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Template file not found at '{template_path}'. Make sure it's in the same directory as the script.")
        sys.exit(1)

def create_html_from_json(json_filepath, html_filepath, template_content):
    """
    Creates a single HTML file from a JSON file using a template.
    """
    try:
        with open(json_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        title = data.get('title', 'Article')
        content = data.get('content', '<p>No content found.</p>')

        # Clean up empty paragraphs and paragraphs containing only comments/whitespace
        # Pattern: <p> followed by any sequence of whitespace OR comments, followed by </p>
        # We use \s instead of \s* inside the group to avoid catastrophic backtracking
        content = re.sub(r'<p>(?:\s|<!--.*?-->)*</p>', '', content, flags=re.DOTALL)
        # Also remove paragraphs containing only break tags
        content = re.sub(r'<p>\s*<br\s*/?>\s*</p>', '', content, flags=re.IGNORECASE)

        # Fix nested paragraphs which cause layout issues (extra spacing)
        # Replace <p>...<p> with <p> (effectively removing the outer start tag)
        content = re.sub(r'<p>(\s*<p>)', r'\1', content, flags=re.IGNORECASE)
        # Replace </p>...</p> with </p> (removing the outer end tag)
        content = re.sub(r'</p>(\s*</p>)', r'\1', content, flags=re.IGNORECASE)

        # Replace placeholders in the template with actual data
        output_html = template_content.replace('{TITLE}', title)
        output_html = output_html.replace('{CONTENT}', content)

        with open(html_filepath, 'w', encoding='utf-8') as f:
            f.write(output_html)

    except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
        print(f"Skipping {json_filepath} due to an error: {e}")

def process_articles_directory(root_dir, template_content):
    """
    Walks through a directory, finds all .json files, and converts them.
    """
    print(f"Starting to process directory: {root_dir}")
    if not os.path.isdir(root_dir):
        print(f"Error: '{root_dir}' is not a valid directory.")
        return []

    generated_html_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.json'):
                json_filepath = os.path.join(dirpath, filename)
                
                # Place generated HTML inside a 'web' subdirectory
                web_dir = os.path.join(dirpath, 'web')
                os.makedirs(web_dir, exist_ok=True)
                
                base_name = os.path.splitext(filename)[0]
                html_filepath = os.path.join(web_dir, base_name + '.html')
                
                print(f"  - Converting '{json_filepath}'")
                create_html_from_json(json_filepath, html_filepath, template_content)
                generated_html_files.append(html_filepath)
    
    print(f"\nProcessing complete. Converted {len(generated_html_files)} files.")
    return generated_html_files

def generate_main_index(html_paths, root_dir):
    """Generates a main index.html file with a simple list of all created files."""
    print("\nGenerating main index file...")
    if not html_paths:
        print("No HTML files were generated, skipping index file creation.")
        return

    # Create relative paths from the root directory for cleaner links
    list_items = [f'<li><a href="{os.path.relpath(path, root_dir).replace(os.sep, "/")}">{os.path.relpath(path, root_dir)}</a></li>' for path in sorted(html_paths)]
    
    list_html = "<ul>\n" + "\n".join(list_items) + "\n</ul>"

    index_html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Article Index</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            /* Default to Dark Theme */
            --primary-color: #3b82f6;
            --bg-body: #0f172a;
            --bg-surface: #1e293b;
            --border-color: #334155;
            --text-primary: #f8fafc;
            --text-secondary: #cbd5e1;
            --link-color: #60a5fa;
            --radius-lg: 8px;
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
        }}
        body {{ 
            font-family: 'Inter', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6; 
            max-width: 800px; 
            margin: 0 auto; 
            padding: 2rem; 
            background-color: var(--bg-body); 
            color: var(--text-primary); 
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }}
        h1 {{ 
            color: var(--text-primary); 
            border-bottom: 1px solid var(--border-color); 
            padding-bottom: 1rem; 
            margin-bottom: 2rem;
        }}
        ul {{ 
            list-style-type: none; 
            padding: 0; 
            background-color: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-md);
            overflow: hidden;
        }}
        li {{ 
            margin: 0; 
            border-bottom: 1px solid var(--border-color); 
            padding: 0;
        }}
        li:last-child {{ border-bottom: none; }}
        a {{ 
            display: block;
            padding: 1rem;
            text-decoration: none; 
            color: var(--link-color); 
            transition: background-color 0.2s;
        }}
        a:hover {{ 
            background-color: var(--border-color);
            text-decoration: none; 
        }}
        @media (max-width: 768px) {{
            body {{ padding: 0; }}
            h1 {{ padding-left: 1rem; padding-right: 1rem; }}
            ul {{ border-radius: 0; border: none; border-top: 1px solid var(--border-color); border-bottom: 1px solid var(--border-color); }}
        }}
    </style>
</head>
<body>
    <h1>Generated Articles Index</h1>
    {list_html}
</body>
</html>
"""
    index_filepath = os.path.join(root_dir, 'index.html')
    with open(index_filepath, 'w', encoding='utf-8') as f:
        f.write(index_html_content)
    
    print(f"Successfully created main index at '{os.path.abspath(index_filepath)}'")

def run_asset_localization(articles_dir):
    """
    Runs the localize_assets.py script on the directory where HTML was generated.
    """
    print("\n--- Running asset localization ---")
    script_path = os.path.join(os.path.dirname(__file__), 'localize_assets.py')
    
    if not os.path.exists(script_path):
        print(f"Warning: localize_assets.py not found at '{script_path}'. Skipping localization.")
        return
        
    try:
        # We run the script on the root articles directory and add the verbose flag.
        # It will find all the .html files inside it recursively.
        command = [sys.executable, script_path, articles_dir, "-v"]
        print(f"Executing: {' '.join(command)}")
        # Removed capture_output=True to allow the subprocess to print in real-time.
        subprocess.run(command, check=True, text=True)
        print("--- Asset localization complete ---")
    except subprocess.CalledProcessError as e:
        print("\n--- Asset localization FAILED ---")
        print(f"Error running localize_assets.py. The script exited with a non-zero status.")
        # The subprocess's stderr will be printed to the console automatically.
    except FileNotFoundError:
        print(f"Error: '{sys.executable}' not found. Cannot run subprocess.")


# --- Main execution ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python render_article.py <path_to_articles_directory>")
        sys.exit(1)

    template = read_template()
    articles_dir = sys.argv[1]
    
    # 1. Generate HTML files from JSON
    generated_files = process_articles_directory(articles_dir, template)
    
    if generated_files:
        # 2. Create the main index.html
        generate_main_index(generated_files, articles_dir)
        
        # 3. Run the asset localizer on the output directory
        run_asset_localization(articles_dir)

