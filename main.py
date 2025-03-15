from src.vcs import check_for_updates
check_for_updates()

import os
from googleapiclient.discovery import build

import locale
locale.setlocale(locale.LC_TIME, "fr_FR")

from src.pdf_processing import *
from src.image_processing import *
from src.utils import *
from src.constants import *
from src.drive_upload import *
from src.process_letters import create_combine_letters

def main():
    # Authenticate Google Drive once and get the service instances
    creds = authenticate_google_drive()
    drive_service = build('drive', 'v3', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)
    check_for_tesseract()
    
    clear_display()
    print("1. Separate-Pdfs")
    print("2. Separate-Handwritten-Pdfs")
    print("3. Create Letters")
    print("\nEnter your choice (1/2): ")
    
    while True:
        choice = getch()
        print(choice)
        if choice == "1":
            print("\nLoading...")
            separate_pdfs(sheets_service, drive_service)
            break
        elif choice == "2":
            print("\nLoading...")
            separate_handwritten_pdfs(sheets_service, drive_service)
            break
        elif choice == "3":
            print("\nLoading...")
            create_combine_letters(sheets_service, drive_service)
            break
        
    print("\n\nAll Files Completed")
    countdown("Exit", 3)



if __name__ == "__main__":
    os.makedirs(NORMAL_INPUT_FOLDER, exist_ok=True)
    os.makedirs(HANDWRITTEN_INPUT_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    os.makedirs(IMAGE_FOLDER, exist_ok=True)
    os.makedirs(COMPLETED_FOLDER, exist_ok=True)
    os.makedirs(LETTER_FOLDER, exist_ok=True)
    os.makedirs(TEMP_LETTER_FOLDER, exist_ok=True)
    main()