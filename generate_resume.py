import os
import subprocess
import io
import json
import re
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload

# --- Configuration ---
RAW_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
GOOGLE_DOC_ID = os.environ.get("GOOGLE_DOC_FILE_ID")
OUTPUT_HTML_PATH = "docs/index.html"

def get_drive_service():
    """Authenticates using the raw JSON string and returns the Drive service object."""
    if not RAW_SERVICE_ACCOUNT_JSON or not GOOGLE_DOC_ID:
        raise ValueError("Missing required environment variables: GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_DOC_FILE_ID.")

    try:
        info = json.loads(RAW_SERVICE_ACCOUNT_JSON)
        creds = Credentials.from_service_account_info(
            info, 
            scopes=[
                'https://www.googleapis.com/auth/drive.readonly', 
                'https://www.googleapis.com/auth/documents.readonly'
            ]
        )
    except json.JSONDecodeError:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON environment variable is not valid JSON.")
    except Exception as e:
        raise RuntimeError(f"Failed to load credentials: {e}")

    service = build('drive', 'v3', credentials=creds)
    return service

def download_google_doc(service, file_id):
    """Downloads a file from Google Drive, auto-detecting if it needs export or direct download."""
    print("Fetching file metadata...")
    try:
        meta = service.files().get(fileId=file_id, fields="mimeType, name").execute()
        mime_type = meta.get("mimeType")
        print(f"Detected File Type: {mime_type}")

        if mime_type == "application/vnd.google-apps.document":
            print("Target is a native Google Doc. Exporting to DOCX format...")
            request = service.files().export_media(
                fileId=file_id,
                mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
        else:
            print("Target is a standard binary file. Downloading directly via get_media...")
            request = service.files().get_media(fileId=file_id)

        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"Download progress: {int(status.progress() * 100)}%")

        temp_docx_path = "temp_download.docx"
        with open(temp_docx_path, "wb") as f:
            f.write(fh.getvalue())
        
        print(f"Successfully saved document to {temp_docx_path}")
        return temp_docx_path

    except Exception as e:
        print(f"Google Drive API error details: {e}")
        raise Exception(f"Failed to retrieve file content from Google Drive due to: {e}")

def convert_docx_to_html(docx_path, output_path):
    """Converts a DOCX file to HTML using Pandoc."""
    print("Starting Pandoc conversion...")
    try:
        subprocess.run([
            "pandoc", 
            "-s", 
            docx_path, 
            "-t", 
            "html", 
            "-o", 
            output_path
        ], check=True, capture_output=True)
        print(f"Conversion successful. HTML saved to {output_path}")
    except subprocess.CalledProcessError as e:
        print("Pandoc conversion failed. Check dependencies and document format.")
        print(f"STDOUT: {e.stdout.decode()}")
        print(f"STDERR: {e.stderr.decode()}")
        raise RuntimeError("Pandoc conversion failed.")
    except FileNotFoundError:
        print("Error: 'pandoc' command not found. Please ensure Pandoc is installed.")
        raise

def main():
    """Main orchestration function."""
    try:
        drive_service = get_drive_service()
        docx_path = download_google_doc(drive_service, GOOGLE_DOC_ID)

        convert_docx_to_html(docx_path, OUTPUT_HTML_PATH)

        # HTML Sanitization and Custom CSS Injection
        if os.path.exists(OUTPUT_HTML_PATH):
            print("Refining HTML structure and injecting modern styling...")
            with open(OUTPUT_HTML_PATH, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Clean out structural junk created by the converter
            # Strip blockquotes wrapped around text or lists
            html_content = re.sub(r'<blockquote>\s*<p>(.*?)</p>\s*</blockquote>', r'<p>\1</p>', html_content, flags=re.DOTALL)
            html_content = re.sub(r'<blockquote>\s*(<ul>.*?</ul>)\s*</blockquote>', r'\1', html_content, flags=re.DOTALL)
            html_content = re.sub(r'<li>\s*<blockquote>\s*<p>(.*?)</p>\s*</blockquote>\s*</li>', r'<li>\1</li>', html_content, flags=re.DOTALL)
            
            # Strip out highlighting mark tags if any exist
            html_content = html_content.replace("<mark>", "").replace("</mark>", "")

            # Inject styles
            modern_head = """<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Mark Roe - Senior DevOps Engineer</title>
  <style>
    :root {
      --primary: #1e293b;
      --secondary: #475569;
      --accent: #2563eb;
      --text: #334155;
      --bg: #f8fafc;
      --line: #e2e8f0;
    }
    
    html {
      background-color: var(--bg);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      font-size: 15px;
      line-height: 1.6;
      color: var(--text);
    }

    body {
      margin: 2rem auto;
      max-width: 50rem;
      background: #ffffff;
      padding: 3rem;
      box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05), 0 2px 4px -2px rgb(0 0 0 / 0.05);
      border-radius: 8px;
    }

    /* Header styling optimization */
    p:first-of-type {
      text-align: center;
      font-size: 1.8rem;
      font-weight: 800;
      color: var(--primary);
      margin-bottom: 0.25rem;
    }

    p:first-of-type + p {
      text-align: center;
      margin-top: 0;
      color: var(--secondary);
      font-size: 0.95rem;
      border-bottom: 2px solid var(--primary);
      padding-bottom: 1.5rem;
      margin-bottom: 2rem;
    }

    p:first-of-type + p a {
      color: var(--accent);
      text-decoration: none;
      margin: 0 0.5rem;
    }
    
    p:first-of-type + p a:hover {
      text-decoration: underline;
    }

    /* Document Sections */
    p > strong:only-child {
      display: block;
      font-size: 1.25rem;
      color: var(--primary);
      border-bottom: 1px solid var(--line);
      margin-top: 2rem;
      margin-bottom: 1rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    /* Skills block adjustment */
    p strong {
      color: var(--primary);
    }

    /* Job Titles & Subheadings */
    p + p > strong:only-child {
      border-bottom: none;
      text-transform: none;
      font-size: 1.1rem;
      margin-top: 1rem;
      margin-bottom: 0;
    }

    /* List formatting */
    ul {
      padding-left: 1.2rem;
      margin-top: 0.5rem;
    }

    li {
      margin-bottom: 0.4rem;
    }

    /* Print styling rules */
    @media print {
      html { background-color: #fff; }
      body {
        margin: 0;
        padding: 0;
        box-shadow: none;
        max-width: 100%;
        font-size: 11pt;
      }
      p > strong:only-child {
        margin-top: 1.5rem;
        page-break-after: avoid;
      }
      li { page-break-inside: avoid; }
    }

    /* Mobile view styling */
    @media (max-width: 640px) {
      body { padding: 1.5rem; margin: 1rem; }
      html { font-size: 14px; }
    }
  </style>
</head>"""


            html_content = re.sub(r'<head>.*?</head>', modern_head, html_content, flags=re.DOTALL)

            with open(OUTPUT_HTML_PATH, "w", encoding="utf-8") as f:
                f.write(html_content)
            print("HTML beautifully polished and saved.")


        if os.path.exists(docx_path):
            os.remove(docx_path)
            print("Cleanup complete.")

    except (ValueError, FileNotFoundError, RuntimeError, Exception) as e:
        print(f"CRITICAL FAILURE: {e}")
        raise

if __name__ == "__main__":
    main()