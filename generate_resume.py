import os
import subprocess
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload
import io
import json

# --- Configuration ---
RAW_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
GOOGLE_DOC_ID = os.environ.get("GOOGLE_DOC_FILE_ID")
OUTPUT_HTML_PATH = "docs/index.html"

def get_drive_service():
    """Authenticates and returns the Google Drive service object."""
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
        # 1. Fetch file metadata to see its mimeType
        meta = service.files().get(fileId=file_id, fields="mimeType, name").execute()
        mime_type = meta.get("mimeType")
        print(f"Detected File Type: {mime_type}")

        # 2. Set up request based on file type
        if mime_type == "application/vnd.google-apps.document":
            print("Target is a native Google Doc. Exporting to DOCX format...")
            request = service.files().export_media(
                fileId=file_id,
                mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
        else:
            print("Target is a standard binary file. Downloading directly via get_media...")
            request = service.files().get_media(fileId=file_id)

        # 3. Download the binary stream chunks
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
        # Ensure pandoc is installed system-wide in the runner environment
        subprocess.run([
            "pandoc", 
            "-s",        # Standalone document
            docx_path, 
            "-t",        # Target format
            "html", 
            "-o",        # Output file
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
        # 1. Authentication and Download
        drive_service = get_drive_service()
        docx_path = download_google_doc(drive_service, GOOGLE_DOC_ID)

        # 2. Conversion
        convert_docx_to_html(docx_path, OUTPUT_HTML_PATH)

        # 3. Cleanup (optional)
        os.remove(docx_path)
        print("Cleanup complete.")

    except (ValueError, FileNotFoundError, RuntimeError, Exception) as e:
        print(f"CRITICAL FAILURE: {e}")
        # Re-raise the exception so the GitHub Action fails clearly
        raise

if __name__ == "__main__":
    main()