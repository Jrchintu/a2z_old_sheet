import json
import sys
import os
import subprocess
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
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.6; max-width: 900px; margin: 40px auto; padding: 0 20px; }}
        h1 {{ color: #2c3e50; }}
        ul {{ list-style-type: none; padding: 0; }}
        li {{ margin: 8px 0; border-left: 3px solid #ecf0f1; padding-left: 15px; }}
        a {{ text-decoration: none; color: #3498db; }}
        a:hover {{ text-decoration: underline; }}
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

