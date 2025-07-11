from io import BytesIO
import os
import shutil
import fitz
from tqdm import tqdm
from PIL import Image

from .undertaker import get_undertaker_data

from .drive_upload import get_table_data

from .constants import *
from .image_processing import *
from pprint import pprint

def combine_images_to_pdf(image_paths, output_pdf_path):
    if not image_paths:
        return

    # If only one image, save it as a PDF directly
    if len(image_paths) == 1:
        img = Image.open(image_paths[0])
        img.convert("RGB").save(output_pdf_path)
        return output_pdf_path

    # Open the images
    images = [Image.open(image) for image in image_paths]

    # Convert all images to RGB (some formats may be in different modes)
    images = [img.convert("RGB") for img in images]

    # Save images as a PDF
    images[0].save(output_pdf_path, save_all=True, append_images=images[1:])

    return output_pdf_path


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

    for i in tqdm(
        range(len(doc)),
        ncols=60,
        bar_format="{percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}",
    ):
        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=fitz.Matrix(resolution / 72, resolution / 72))
        
        # Convert to Pillow Image
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Compress until under 800 KB
        image_path = os.path.join(output_folder, f"page-{i + 1}.png")
        for quality in range(95, 10, -5):  # Try decreasing quality in steps
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=quality, optimize=True)
            size_kb = buffer.tell() / 1024
            if size_kb <= 900:
                with open(image_path, "wb") as f:
                    f.write(buffer.getvalue())
                break
        else:
            print(f"Warning: page-{i + 1} image couldn't be reduced below 800 KB.")

    doc.close()


def separate_pdfs(sheets_service, drive_service):
    openai_client = OpenAI(api_key=GPT_KEY_1)
    existing_images = get_table_data(sheets_service, IMAGE_SHEET_ID, "Sheet1!A:D")
    pdf_files = [
        file
        for file in os.listdir(INPUT_FOLDER)
        if file.lower().endswith(".pdf")
    ]
    undertaker_data = get_undertaker_data(sheets_service)
    for pdf in pdf_files:
        notary_images = []
        undertake_images = []
        Hospital_images = []
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
            gpt_result: dict = get_image_result(
                image_path, openai_client
            )  # Pass services
            if gpt_result:
                details = list(dict(gpt_result["about_deceased_person"]).values())
                (
                    name,
                    dob,
                    dod,
                    city,
                    dep,
                    death_city,
                    declarant,
                    declarant_address,
                    declarant_city,
                    zip_code,
                    relation,
                    partner,
                    notary_name
                ) = details
                
                # pprint(gpt_result)
                image_link = upload_image_and_append_sheet(
                    name,
                    dob,
                    dod,
                    image_path,
                    drive_service,
                    sheets_service,
                    existing_images,
                )
                other, template = False, 2
                try:
                    if int(dep) in [6, 75, 78, 92]:
                        time_checked = is_before(dod, 2018)
                        print(f"Before 2018 (06, 75, 78, 92) : {time_checked}")
                    else:
                        time_checked = is_before(dod, 2020)
                        print(f"Before 2020 : {time_checked}")
                except:
                    time_checked = is_before(dod, 2020)

                if int(gpt_result["notary"]):
                    print("Notary")
                    notary_images.append(image_path)
                    notary_first_name, notary_last_name = get_fname_lname(
                        unidecode(notary_name)
                    )
                    new_row = (
                        notary_first_name,
                        notary_last_name,
                        None,
                        None,
                        name,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        image_link,
                    )
                    request = (
                        sheets_service.spreadsheets()
                        .values()
                        .append(
                            spreadsheetId=ANNUAIRE_NOTAIRES_SHEET_ID,
                            range="Scheduled email!A:M",
                            valueInputOption="USER_ENTERED",
                            body={"values": [new_row]},
                        )
                    )
                    execute_with_retry(request)
                elif int(gpt_result["undertaker"]):
                    if time_checked:
                        template = 1
                        other = True
                    else:
                        print("Undertaker")
                        undertake_images.append(image_path)
                        clean_declarant = unidecode(declarant).replace(" ", "").replace("-", "").replace(",", "").lower()
                        if declarant and clean_declarant not in undertaker_data:
                            new_row = (
                                None,
                                dep,
                                unidecode(declarant).replace("-", " "),
                                declarant_city,
                                declarant_address,
                                None,
                                None,
                                "Not contacted"
                            )
                            request = (
                                sheets_service.spreadsheets()
                                .values()
                                .append(
                                    spreadsheetId=ANNUAIRE_UNDERTAKER_SHEET_ID,
                                    range="PF Annuaire!A:H",
                                    valueInputOption="USER_ENTERED",
                                    body={"values": [new_row]},
                                )
                            )
                            execute_with_retry(request)
                        new_row = (
                            None,
                            unidecode(declarant).replace("-", " "),
                            None,
                            None,
                            name,
                            dod,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            image_link
                        )
                        request = (
                            sheets_service.spreadsheets()
                            .values()
                            .append(
                                spreadsheetId=ANNUAIRE_UNDERTAKER_SHEET_ID,
                                range="Scheduled email!A:C",
                                valueInputOption="USER_ENTERED",
                                body={"values": [new_row]},
                            )
                        )
                        execute_with_retry(request)
                elif int(gpt_result["hospital"]):
                    print("Hospital")
                    Hospital_images.append(image_path)
                    new_row = (
                        death_city,
                        declarant_address,
                        None,
                        None,
                        name,
                        dod,
                        declarant,
                        "louis.fleury@klero.fr",
                        None,
                        None,
                        None,
                        None,
                        None,
                        image_link,
                    )
                    request = (
                        sheets_service.spreadsheets()
                        .values()
                        .append(
                            spreadsheetId=ANNUAIRE_HOSPITAL_SHEET_ID,
                            range="Scheduled email!A:N",
                            valueInputOption="USER_ENTERED",
                            body={"values": [new_row]},
                        )
                    )
                    execute_with_retry(request)
                elif int(gpt_result["heir"]):
                    if time_checked:
                        other = True
                    else:
                        print("Heir")
                        heir_images.append(image_path)
                        new_row = (
                            name,
                            dod,
                            death_city,
                            declarant,
                            declarant_address,
                            declarant_city,
                            zip_code,
                            relation,
                            partner,
                            image_link,
                            "Not contacted",
                            "",
                            "",
                            "A vérifier",
                        )
                        request = (
                            sheets_service.spreadsheets()
                            .values()
                            .append(
                                spreadsheetId=ANNUAIRE_HERITIERS_SHEET_ID,
                                range="Héritier Annuaire!A:N",
                                valueInputOption="USER_ENTERED",
                                body={"values": [new_row]},
                            )
                        )

                        execute_with_retry(request)
                else:
                    other = True

                if other:
                    print("Other")
                    na_images.append(image_path)
                    new_row = (
                        unidecode(city).replace("-", " "),
                        dep,
                        None,
                        None,
                        name,
                        dod,
                        "louis.fleury@klero.fr",
                        None,
                        None,
                        None,
                        None,
                        None,
                        image_link,
                        template,
                    )
                    request = (
                        sheets_service.spreadsheets()
                        .values()
                        .append(
                            spreadsheetId=ANNUAIRE_TOWNHALL_SHEET_ID,
                            range="Scheduled email!A:N",
                            valueInputOption="USER_ENTERED",
                            body={"values": [new_row]},
                        )
                    )
                    execute_with_retry(request)
                print("------------------------------------")
        combine_images_to_pdf(
            notary_images,
            f"{OUTPUT_FOLDER}/{pdf_name.replace('.pdf', ' - Notary.pdf')}",
        )
        combine_images_to_pdf(
            heir_images,
            f"{OUTPUT_FOLDER}/{pdf_name.replace('.pdf', ' - Heir.pdf')}",
        )
        combine_images_to_pdf(
            Hospital_images,
            f"{OUTPUT_FOLDER}/{pdf_name.replace('.pdf', ' - Hospital.pdf')}",
        )
        combine_images_to_pdf(
            na_images,
            f"{OUTPUT_FOLDER}/{pdf_name.replace('.pdf', ' - Other.pdf')}",
        )
        combine_images_to_pdf(
            undertake_images,
            f"{OUTPUT_FOLDER}/{pdf_name.replace('.pdf', ' - Undertaker.pdf')}",
        )

        shutil.move(pdf_path, f"{COMPLETED_FOLDER}/{pdf}")

        print(
            f"Completed processing for {pdf_name} in {int(time.time() - time_start)} sec"
        )