import os
import sys
from time import sleep
import time

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    base_path = getattr(
        sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    )
    return os.path.join(base_path, relative_path)


def extract_number(filename: str):
    return int(filename.split("-")[1].split(".")[0])

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