import os
import subprocess
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
import io

# --- Configuration ---
SERVICE_ACCOUNT_FILE = os.environ.get("SERVICE_ACCOUNT_JSON_PATH")
SPREADSHEET_ID = os.environ.get("GOOGLE_DOC_FILE_ID")
OUTPUT_HTML_PATH = "docs/index.html"

def get_drive_service():
    """Authenticates and returns the Google Drive service object."""
    if not SERVICE_ACCOUNT_FILE or not SPREADSHEET_ID:
        raise ValueError("Missing required environment variables: SERVICE_ACCOUNT_JSON_PATH or GOOGLE_DOC_FILE_ID.")

    creds = None
    # Assume credentials file is available from the environment
    try:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/drive.metadata.readonly', 'https://www.googleapis.com/auth/documents.readonly'])
    except FileNotFoundError:
        raise FileNotFoundError(f"Credentials file not found at: {SERVICE_ACCOUNT_FILE}")

    service = build('drive', 'v3', credentials=creds)
    return service

def download_google_doc(service, file_id):
    """Downloads the Google Doc file content."""
    print("Downloading Google Doc...")
    # Exporting as native format is required for download
    request = service.files().get(fileId=file_id).execute()
    file_data = request.get('content')

    if not file_data:
        raise Exception("Failed to retrieve file content from Google Drive.")

    # The downloaded content needs to be saved to a temporary file path
    temp_docx_path = "temp_download.docx"
    with open(temp_docx_path, "wb") as f:
        f.write(file_data)
    
    print(f"Successfully downloaded document to {temp_docx_path}")
    return temp_docx_path

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
        docx_path = download_google_doc(drive_service, SPREADSHEET_ID)

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