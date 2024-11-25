import os
import re
import sys
from time import sleep
from getch import getch as pygetch
import time

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    base_path = getattr(
        sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    )
    return os.path.join(base_path, relative_path)


def clear_display():
    os.system("cls" if os.name == "nt" else "clear")

def extract_number(filename: str):
    return int(filename.split("-")[1].split(".")[0])

def getch():
    if sys.platform == "win32":
        return pygetch().decode().lower()
    else:
        return pygetch().lower()

def countdown(text: str, t: int):
    while t >= 0:
        print(f"{text} : {t} sec", end="\r")
        sleep(1)
        t -= 1
    print()
    
def execute_with_retry(request, retries=10, initial_delay=1):
    """
    Execute a Google API request with retry logic and exponential backoff.
    
    :param request: The API request to execute.
    :param retries: The number of retries.
    :param initial_delay: Initial delay for exponential backoff.
    :return: The response from the request if successful.
    """
    delay = initial_delay
    for attempt in range(retries):
        try:
            return request.execute()
        except Exception as e:
            print(f"Error {e}: Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 2  # Exponential backoff
    raise Exception(f"Max retries reached for request: {request.uri}")

def normalize_rows(data, target_length):
    normalized_data = []
    for row in data:
        # Pad the row with empty strings if it's shorter than the target length
        while len(row) < target_length:
            row.append("")
        # Trim the row if it's longer than the target length (unlikely in this case)
        if len(row) > target_length:
            row = row[:target_length]
        normalized_data.append(row)
    return normalized_data

# Extract file ID from Google Drive link
def extract_file_id(drive_link):
    match = re.search(r"[-\w]{25,}", drive_link)
    if match:
        return match.group(0)
    else:
        raise ValueError("Invalid Google Drive link")