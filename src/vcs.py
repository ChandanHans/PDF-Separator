import base64
import os
import sys
import socket
import requests
import datetime
import subprocess


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    base_path = getattr(
        sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    )
    return os.path.join(base_path, relative_path)


OWNER = "ChandanHans"
REPO_NAME = "PDF2GS-Separator"
EXE_NAME = f"{REPO_NAME}.exe"
RELEASE_TAG = "v1.0.0"
EXE_URL = (
    f"https://github.com/{OWNER}/{REPO_NAME}/releases/download/{RELEASE_TAG}/{EXE_NAME}"
)
REPO_API_URL = (
    f"https://api.github.com/repos/{OWNER}/{REPO_NAME}/git/trees/main?recursive=1"
)
LOCAL_TIME_PATH = resource_path("time.txt")
UPDATER_EXE_PATH = resource_path("updater.exe")
EXE_PATH = sys.executable


def get_local_version_time():
    """Read the version date from the local version file."""
    with open(LOCAL_TIME_PATH, "r") as file:
        return datetime.datetime.strptime(file.read().strip(), "%Y-%m-%dT%H:%M:%SZ")


def get_latest_release_time():
    """Fetch the latest release time from the GitHub repository."""
    # Fetch the release by tag
    response = requests.get(
        f"https://api.github.com/repos/{OWNER}/{REPO_NAME}/releases/tags/{RELEASE_TAG}"
    )
    release_info = response.json()

    required_asset = None
    for asset in release_info.get("assets", []):
        if asset["name"] == EXE_NAME:
            required_asset = asset
            break

    if not required_asset:
        print("No release information found.")
        return None

    release_time = datetime.datetime.strptime(
        required_asset["updated_at"], "%Y-%m-%dT%H:%M:%SZ"
    )
    return release_time


def is_my_machine():
    my_machine_list = ["CHANDAN-ASUS"]
    return socket.gethostname() in my_machine_list


def update_local_files():
    updated = False
    response = requests.get(REPO_API_URL)
    if response.status_code != 200:
        print(f"Failed to fetch repository data: {response.status_code}")
        return updated

    files = response.json().get("tree", [])
    python_files = [file for file in files if file["path"].endswith(".py")]
    for file in python_files:
        file_url = file["url"]
        download_response = requests.get(file_url)
        if download_response.status_code == 200:
            file_content_encoded = download_response.json()["content"]
            file_content = base64.b64decode(file_content_encoded).decode(
                "utf-8"
            )  # Decode from base64
            file_path = os.path.join(os.getcwd(), file["path"])
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            local_content = ""
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    local_content = f.read()
            except:
                pass
            if local_content != file_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(file_content)
                updated = True
                print(f"Updated: {file['path']}")
        else:
            print(f"Failed to download {file['path']}: {download_response.status_code}")
    return updated


def check_for_updates():
    """Check if an update is available based on the latest commit date."""
    print("Checking for updates...")
    if getattr(sys, "frozen", False):
        try:
            local_version_date = get_local_version_time()
        except:
            return
        remote_version_date = get_latest_release_time()

        if remote_version_date is None:
            return
        # Calculate the difference in time
        time_difference = remote_version_date - local_version_date
        # Check if the difference is greater than 2 minutes
        if time_difference > datetime.timedelta(minutes=2):
            try:
                subprocess.Popen([UPDATER_EXE_PATH, EXE_PATH, EXE_URL])
            except:
                input("ERROR : Contact Chandan")
            sys.exit()
    # else:
    #     if not is_my_machine() and update_local_files():
    #         print("Script Updated")
    #         input("Please close this app and restart it again")
    #         sys.exit()
