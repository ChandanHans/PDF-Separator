# main.py
from src.vcs import check_for_updates

check_for_updates()

import os
import time
import shutil
from tqdm import tqdm

from src.pdf_processing import *
from src.image_processing import *
from src.utils import *
from src.constants import *

def main():
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
        images = sorted(images, key=extract_number)

        print("\nSTART :\n")
        progress_bar = tqdm(images, ncols=60, bar_format="{percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}")
        for image in progress_bar:
            image_path = f"{IMAGE_FOLDER}/{image}"
            result:dict = get_image_result(image_path)  # Pass services
            if result:
                results = list(result.values())
                if results[1]:
                    notary_images.append(image_path)
                elif results[2]:
                    if results[0]:
                        na_images.append(image_path)
                    else:
                        undertake_images.append(image_path)
                else:
                    na_images.append(image_path)

        combine_images_to_pdf(notary_images,f"{NOTARY_OUTPUT_FOLDER}/{pdf_name.replace('.pdf', ' - Notary.pdf')}")
        combine_images_to_pdf(undertake_images,f"{UNDERTAKER_OUTPUT_FOLDER}/{pdf_name.replace('.pdf', ' - Undertaker.pdf')}")
        combine_images_to_pdf(na_images,f"{OTHER_OUTPUT_FOLDER}/{pdf_name.replace('.pdf', ' - Other.pdf')}")
        shutil.move(pdf_path, f"{COMPLETED_FOLDER}/{pdf}")
        
        print(f"Completed processing for {pdf_name} in {int(time.time() - time_start)} sec")

    print("\n\nAll Files Completed")
    countdown("Exit", 3)


if __name__ == "__main__":
    if not os.path.exists(INPUT_FOLDER):
        os.makedirs(INPUT_FOLDER)
    if not os.path.exists(NOTARY_OUTPUT_FOLDER):
        os.makedirs(NOTARY_OUTPUT_FOLDER)
    if not os.path.exists(UNDERTAKER_OUTPUT_FOLDER):
        os.makedirs(UNDERTAKER_OUTPUT_FOLDER)
    if not os.path.exists(OTHER_OUTPUT_FOLDER):
        os.makedirs(OTHER_OUTPUT_FOLDER)
    if not os.path.exists(IMAGE_FOLDER):
        os.makedirs(IMAGE_FOLDER)
    if not os.path.exists(COMPLETED_FOLDER):
        os.makedirs(COMPLETED_FOLDER)
    main()