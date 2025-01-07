import os
import shutil
import fitz
from tqdm import tqdm
from PIL import Image

from .drive_upload import get_table_data

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

def pdf_to_images(pdf_path, output_folder, resolution):
    delete_images(output_folder)
    print("\nGetting All Images From PDF...")
    doc = fitz.open(pdf_path)
    
    for i in tqdm(range(len(doc)), ncols=60, bar_format="{percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}"):
        page = doc.load_page(i)
        # Get the image of the page
        image = page.get_pixmap(matrix=fitz.Matrix(resolution / 72, resolution / 72))
        image_path = f"{output_folder}/page-{i + 1}.png"
        image.save(image_path)
    
    doc.close()
    

def separate_pdfs(sheets_service, drive_service):
    
    existing_images = get_table_data(sheets_service, IMAGE_SHEET_ID, "Sheet1!A:B")
    pdf_files = [
        file for file in os.listdir(INPUT_FOLDER) if file.lower().endswith(".pdf")
    ]

    for pdf in pdf_files:
        notary_images = []
        undertake_images = []
        heir_images = []
        na_images = []
        
        pdf_name = os.path.basename(pdf)
        pdf_path = f"{INPUT_FOLDER}/{pdf}"

        time_start = time.time()
        print(f"\nProcess Started For {pdf_name}\n")
        # Convert PDF to images
        pdf_to_images(pdf_path, IMAGE_FOLDER, 200)

        images = [
            file for file in os.listdir(IMAGE_FOLDER) if file.lower().endswith(".png")
        ]
        images = sorted(images, key=extract_number)

        print("\nSTART :\n")
        count = 1
        total = len(images)
        for image in images:
            print("------------------------------------")
            print(f"{image} : {count}/{total}")
            count += 1
            
            image_path = f"{IMAGE_FOLDER}/{image}"
            gpt_result:dict = get_image_result(image_path)  # Pass services
            if gpt_result:
                result = list(gpt_result.values())
                details = list(result[4].values())
                name, dod, city, dep, death_city, relative, relative_address, relative_city, zip_code, relation, partner = details
                other, template = False, 2
                if result[3]:
                    time_checked = is_before(dod, 2017)
                    print(f"Before 2017 (Paris) : {time_checked}")
                else:
                    time_checked = is_before(dod, 2019)
                    print(f"Before 2019 : {time_checked}")
                    
                if result[0]:
                    print("Notary")
                    notary_images.append(image_path)
                elif result[1]:
                    if time_checked:
                        template = 1
                        other = True
                    else:
                        print("Undertaker")
                        undertake_images.append(image_path)
                elif result[2]:
                    if time_checked:
                        other = True
                    else:
                        print("Heir")
                        heir_images.append(image_path)
                        file_link = upload_image_and_append_sheet(
                            name, image_path, drive_service, sheets_service, existing_images
                        )
                        new_row = (name, dod, death_city, relative, relative_address, relative_city , zip_code, relation, partner, file_link, "Not contacted","","","A vérifier")
                        request = sheets_service.spreadsheets().values().append(
                                spreadsheetId=ANNUAIRE_HERITIERS_SHEET_ID,
                                range="Héritier Annuaire!A:N",
                                valueInputOption="USER_ENTERED",
                                body={"values": [new_row]},
                            )
                        execute_with_retry(request)
                else:
                    other = True
                
                if other:
                    print("Other")
                    na_images.append(image_path)
                    file_link = upload_image_and_append_sheet(name, image_path, drive_service, sheets_service, existing_images)
                    new_row = (city, dep, None, None, name, dod, "louis.fleury@klero.fr", None, None, None, None, None, file_link, template)
                    request = sheets_service.spreadsheets().values().append(
                            spreadsheetId=ANNUAIRE_TOWNHALL_SHEET_ID,
                            range="Scheduled email!A:N",
                            valueInputOption="USER_ENTERED",
                            body={"values": [new_row]},
                        )
                    execute_with_retry(request)
                print("------------------------------------")
        combine_images_to_pdf(notary_images,f"{NOTARY_OUTPUT_FOLDER}/{pdf_name.replace('.pdf', ' - Notary.pdf')}")
        combine_images_to_pdf(undertake_images,f"{UNDERTAKER_OUTPUT_FOLDER}/{pdf_name.replace('.pdf', ' - Undertaker.pdf')}")
        combine_images_to_pdf(heir_images,f"{HEIR_OUTPUT_FOLDER}/{pdf_name.replace('.pdf', ' - Heir.pdf')}")
        combine_images_to_pdf(na_images,f"{OTHER_OUTPUT_FOLDER}/{pdf_name.replace('.pdf', ' - Other.pdf')}")
        shutil.move(pdf_path, f"{COMPLETED_FOLDER}/{pdf}")
        
        print(f"Completed processing for {pdf_name} in {int(time.time() - time_start)} sec")