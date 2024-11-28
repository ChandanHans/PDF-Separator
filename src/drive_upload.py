# drive_upload.py

import os
import pickle
import re
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload
import io
import requests

from .utils import *
from .constants import CREDS_JSON, TOKEN_FILE

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_user_profile(creds):
    """Retrieve the user's profile information including their name."""
    profile_info_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    headers = {"Authorization": f"Bearer {creds.token}"}
    response = requests.get(profile_info_url, headers=headers)

    if response.status_code == 200:
        user_info = response.json()
        user_name = user_info.get("name", "Unknown")
        return user_name
    else:
        return "Unknown"


def authenticate_google_drive():
    """Authenticate and return the Google Drive service instance with refresh token support."""
    creds = None

    # Load token from file if it exists
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    if creds and creds.expired and creds.refresh_token:
        try:
            print("Refreshing expired token...")
            creds.refresh(Request())  # Automatically refresh the token
            with open(TOKEN_FILE, "wb") as token:
                pickle.dump(creds, token)
        except:
            pass

    # Check if the credentials are valid or can be refreshed
    if creds and creds.valid:
        # Get the current user email from the creds
        current_user = get_user_profile(creds)
        print(f"Current logged-in user: {current_user}")

        # Ask the user if they want to use the current account or log in with a different one
        choice = (
            input("Do you want to use the current account? (y/n): ").strip().lower()
        )
        if choice != "n":
            return creds  # Return the current credentials if the user chooses "current"

    # If no valid credentials, run OAuth flow to get new credentials
    print("No valid credentials found. Please log in.")
    flow = InstalledAppFlow.from_client_config(CREDS_JSON, SCOPES)
    creds = flow.run_local_server(port=0)

    # Save the new credentials to the token file
    with open(TOKEN_FILE, "wb") as token:
        pickle.dump(creds, token)

    return creds


def upload_to_drive(service, file_path, folder_id):
    """Upload a file to Google Drive."""
    file_metadata = {"name": os.path.basename(file_path), "parents": [folder_id]}
    media = MediaFileUpload(file_path, resumable=True)
    request = service.files().create(body=file_metadata, media_body=media, fields="id")
    uploaded_file = execute_with_retry(request)
    file_id = uploaded_file.get("id")
    return file_id


def delete_file_from_drive(service, file_id):
    """Delete a file from Google Drive by its file ID."""
    request = service.files().delete(fileId=file_id)
    execute_with_retry(request)
    print(f"Deleted file with ID {file_id} from Google Drive")



def download_image(drive_service, drive_link, output_path = None):
    """
    Download an image using a Google Drive link.

    Args:
        drive_link (str): The Google Drive link for the image.
        output_path (str): The name of the local file to save the image.
        drive_service: Authenticated Google Drive API service instance.

    Returns:
        str: The path of the saved file.
    """
    file_id = extract_file_id(drive_link)

    # Request the file metadata and download the content
    try:
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

        if not output_path:
            return fh
        
        # Save the file locally
        with open(output_path, "wb") as f:
            f.write(fh.getvalue())
        return output_path
    except Exception as e:
        return None
            
    
def get_table_data(sheets_service, sheet_id, range):
    request = sheets_service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range, 
        )
    result = execute_with_retry(request)
    return result.get("values", [])