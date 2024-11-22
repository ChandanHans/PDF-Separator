import os
import shutil
import fitz
from tqdm import tqdm
from PIL import Image, ImageEnhance

from .constants import *
from .image_processing import *

def combine_images_to_pdf(image_paths, output_pdf_path):
    if not image_paths:
        return
    
    # If only one image, save it as a PDF directly
    if len(image_paths) == 1:
        img = Image.open(image_paths[0])
        img.convert("RGB").save(output_pdf_path)
        return

    # Open the images
    images = [Image.open(image) for image in image_paths]

    # Convert all images to RGB (some formats may be in different modes)
    images = [img.convert("RGB") for img in images]

    # Save images as a PDF
    images[0].save(output_pdf_path, save_all=True, append_images=images[1:])



def delete_images(directory_path):
    try:
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
    except:
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
        pass

def pdf_to_images(pdf_path, output_folder, resolution, contrast_factor=3):
    delete_images(output_folder)
    print("\nGetting All Images From PDF...")
    doc = fitz.open(pdf_path)
    
    for i in tqdm(range(len(doc)), ncols=60, bar_format="{percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}"):
        page = doc.load_page(i)
        # Get the image of the page
        image = page.get_pixmap(matrix=fitz.Matrix(resolution / 72, resolution / 72))
        image_path = f"{output_folder}/page-{i + 1}.png"
        
        # Convert to PIL Image to manipulate contrast
        pil_image = Image.frombytes("RGB", [image.width, image.height], image.samples)
        
        # Enhance the contrast of the image for better OCR
        enhancer = ImageEnhance.Contrast(pil_image)
        enhanced_image = enhancer.enhance(contrast_factor)
        
        # Save the enhanced image
        enhanced_image.save(image_path)
    
    doc.close()
    
def separate_pdfs(sheets_service, drive_service):
    
    existing_images = get_table_data(sheets_service, IMAGE_SHEET_ID, "Sheet1!A:B")
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

        combine_images_to_pdf(notary_images,f"{NOTARY_OUTPUT_FOLDER}/{pdf_name.replace('.pdf', ' - Notary.pdf')}")
        combine_images_to_pdf(undertake_images,f"{UNDERTAKER_OUTPUT_FOLDER}/{pdf_name.replace('.pdf', ' - Undertaker.pdf')}")
        combine_images_to_pdf(na_images,f"{OTHER_OUTPUT_FOLDER}/{pdf_name.replace('.pdf', ' - Other.pdf')}")
        shutil.move(pdf_path, f"{COMPLETED_FOLDER}/{pdf}")
        
        print(f"Completed processing for {pdf_name} in {int(time.time() - time_start)} sec")