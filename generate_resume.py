import os
import subprocess
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
import io
import json  # Add this import at the top of your file!

# --- Configuration ---
# Update this variable name to reflect it's the raw JSON text now
RAW_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
SPREADSHEET_ID = os.environ.get("GOOGLE_DOC_FILE_ID")
OUTPUT_HTML_PATH = "docs/index.html"

def get_drive_service():
    """Authenticates and returns the Google Drive service object."""
    if not RAW_SERVICE_ACCOUNT_JSON or not SPREADSHEET_ID:
        raise ValueError("Missing required environment variables: GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_DOC_FILE_ID.")

    try:
        # Parse the raw string directly into a Python dictionary
        info = json.loads(RAW_SERVICE_ACCOUNT_JSON)
        
        # Use from_service_account_info instead of from_service_account_file
        creds = Credentials.from_service_account_info(
            info, 
            scopes=[
                'https://www.googleapis.com/auth/drive.metadata.readonly', 
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