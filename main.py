# main.py
from src.vcs import check_for_updates

check_for_updates()

import os
import time
import shutil
from tqdm import tqdm
from googleapiclient.discovery import build

from src.pdf_processing import *
from src.image_processing import *
from src.utils import *
from src.constants import *
from src.process_letter import create_pdf_from_template
from src.drive_upload import authenticate_google_drive

def main():
    # Authenticate Google Drive once and get the service instances
    creds = authenticate_google_drive()
    drive_service = build('drive', 'v3', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)


    existing_images = get_existing_image_names(sheets_service, IMAGE_SHEET_ID)
    
    check_for_tesseract()

    pdf_files = [
        file for file in os.listdir(INPUT_FOLDER) if file.lower().endswith(".pdf")
    ]

    for pdf in pdf_files:
        notary_images = []
        undertake_images = []
        na_images = []
        
        pdf_name = os.path.basename(pdf)
        pdf_path = f"{INPUT_FOLDER}/{pdf}"

        time_start = time.time()
        print(f"\nProcess Started For {pdf_name}\n")
        # Convert PDF to images
        pdf_to_images(pdf_path, IMAGE_FOLDER, 200, 3)

        images = [
            file for file in os.listdir(IMAGE_FOLDER) if file.lower().endswith(".png")
        ]
        images = sorted(images, key=extract_number, reverse=True)

        print("\nSTART :\n")
        progress_bar = tqdm(images, ncols=60, bar_format="{percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}")
        for image in progress_bar:
            image_path = f"{IMAGE_FOLDER}/{image}"
            gpt_result:dict = get_image_result(image_path)  # Pass services
            if gpt_result:
                result = list(gpt_result.values())
                if result[1]:
                    notary_images.append(image_path)
                elif result[2]:
                    if result[0]:
                        na_images.append(image_path)
                    else:
                        undertake_images.append(image_path)
                else:
                    if result[0]:
                        na_images.append(image_path)
                    else:
                        details = list(result[3].values())
                        name, dod, city, relative, relative_address, relation = details
                        file_link = upload_image_and_append_sheet(
                            name, image_path, drive_service, sheets_service, existing_images
                        )
                        new_row = (name, dod, city, relative, relative_address, relation, file_link)
                        request = sheets_service.spreadsheets().values().append(
                                spreadsheetId=ANNUAIRE_HERITIERS_SHEET_ID,
                                range="Sheet1!A:G",
                                valueInputOption="RAW",
                                body={"values": [new_row]},
                            )
                        execute_with_retry(request)
                        replacements = {'(NAME)': name}
                        latter_file_name = f"Prise de contact héritier succession {name}.pdf"
                        create_pdf_from_template(replacements, image_path, latter_file_name)

        combine_images_to_pdf(notary_images,f"{NOTARY_OUTPUT_FOLDER}/{pdf_name.replace('.pdf', ' - Notary.pdf')}")
        combine_images_to_pdf(undertake_images,f"{UNDERTAKER_OUTPUT_FOLDER}/{pdf_name.replace('.pdf', ' - Undertaker.pdf')}")
        combine_images_to_pdf(na_images,f"{OTHER_OUTPUT_FOLDER}/{pdf_name.replace('.pdf', ' - Other.pdf')}")
        shutil.move(pdf_path, f"{COMPLETED_FOLDER}/{pdf}")
        
        print(f"Completed processing for {pdf_name} in {int(time.time() - time_start)} sec")

    print("\n\nAll Files Completed")
    countdown("Exit", 3)


if __name__ == "__main__":
    os.makedirs(INPUT_FOLDER, exist_ok=True)
    os.makedirs(NOTARY_OUTPUT_FOLDER, exist_ok=True)
    os.makedirs(UNDERTAKER_OUTPUT_FOLDER, exist_ok=True)
    os.makedirs(OTHER_OUTPUT_FOLDER, exist_ok=True)
    os.makedirs(IMAGE_FOLDER, exist_ok=True)
    os.makedirs(COMPLETED_FOLDER, exist_ok=True)
    os.makedirs(LETTER_FOLDER, exist_ok=True)
    main()