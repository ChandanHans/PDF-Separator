import base64
import os
import platform
import subprocess
import cv2
import pytesseract
from openai import OpenAI
from unidecode import unidecode
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageEnhance, ImageFilter

from .prompts import *
from .constants import *
from .utils import *


def clean_name_for_comparison(name: str):
    """Clean the name by removing spaces, commas, and dashes."""
    return unidecode(name).replace(" ", "").replace(",", "").replace("-", "")


def upload_image_and_append_sheet(
    name, dob, dod, image_path, drive_service, sheets_service, existing_images=None
):
    """
    Upload the image to Google Drive and append its name and link to a Google Sheet.

    If the image already exists in the sheet, skip upload and append.
    """
    # Clean the name for comparison
    cleaned_name = clean_name_for_comparison(name)

    # Check if the image already exists in the sheet
    if existing_images is None:
        existing_images = []  # Ensure there's an empty list if no data is passed
    for image in existing_images:
        if cleaned_name in clean_name_for_comparison(image[0]):
            if len(image) == 4 and (dob != image[-2] or dod != image[-1]):
                continue
            return image[1]

    # Upload the image to the folder
    file_name = f"Acte de décès - {name}.png"
    file_metadata = {"name": file_name, "parents": [DEATH_CERTIFICATES_FOLDER_ID]}
    media = MediaFileUpload(image_path, mimetype="image/png")
    request = drive_service.files().create(
        body=file_metadata, media_body=media, fields="id, webViewLink"
    )
    uploaded_file = execute_with_retry(request)
    # Get the file ID and web link
    file_link = uploaded_file.get("webViewLink")

    # Append the image name and link to the Google Sheet
    row_data = [file_name, file_link, dob, dod]
    request = (
        sheets_service.spreadsheets()
        .values()
        .append(
            spreadsheetId=IMAGE_SHEET_ID,
            range="Sheet1!A:B",
            valueInputOption="USER_ENTERED",
            body={"values": [row_data]},
        )
    )
    execute_with_retry(request)
    existing_images.append(row_data)
    return file_link

def check_handwritten(image_path: str) -> bool:
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    # print(pytesseract.image_to_data(img, lang="fra", config="--oem 1 --psm 6"))
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, lang="fra", config="--oem 1 --psm 6")

    low_conf_count = 0
    total_word_count = 0

    for conf in data['conf']:
        try:
            conf = float(conf)
            if conf > 0:
                total_word_count += 1
                if conf < 70:
                    low_conf_count += 1
        except (ValueError, TypeError):
            continue
    if total_word_count == 0:
        return True
    low_conf_ratio = low_conf_count / total_word_count
    return low_conf_ratio > 0.09

def get_image_result(image_path, openai_client: OpenAI):
    image = process_image_for_ocr(image_path)
    is_handwritten = check_handwritten(image_path)
    print("HandWritten :", is_handwritten)
    full_ocr_text = pytesseract.image_to_string(image, lang="fra", config="--oem 3 --psm 6")
    
    split_by_clarant = unidecode(full_ocr_text).lower().split("clarant", 1)
    split_by_claration = unidecode(full_ocr_text).lower().split("claration", 1)

    declarant_section_text = full_ocr_text
    if len(split_by_claration) > 1:
        declarant_section_text = split_by_claration[-1]
    elif len(split_by_clarant) > 1:
        declarant_section_text = split_by_clarant[-1]
        
    # Step 5: Prepare OpenAI input (Image if handwritten, Text otherwise)
    if is_handwritten:
        base64_string = image_to_base64(image_path)
        extracted_info_response = openai_client.responses.create(
            model="gpt-4o",
            input=[
                {"role": "system", "content": [{"type": "input_text", "text": extract_deceased_info_prompt}]},
                {"role": "user", "content": [{"type": "input_image", "image_url": f"data:image/png;base64,{base64_string}"}]},
            ],
            text={"format": {"type": "json_object"}},
        )
    else:
        extracted_info_response = openai_client.responses.create(
            model="gpt-4o-mini",
            input=[
                {"role": "system", "content": [{"type": "input_text", "text": extract_deceased_info_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": full_ocr_text}]},
            ],
            text={"format": {"type": "json_object"}},
        )

    extracted_info = eval(extracted_info_response.output_text)

    # Step 6: Analyze Declarant
    if is_handwritten:
        declarant_analysis_response = openai_client.responses.create(
            model="gpt-4o",
            input=[
                {"role": "system", "content": [{"type": "input_text", "text": classify_declarant_prompt}]},
                {"role": "user", "content": [{"type": "input_image", "image_url": f"data:image/png;base64,{base64_string}"}]},
            ],
            text={"format": {"type": "json_object"}},
        )
    else:
        deceased_name = list(list(extracted_info.values())[0].values())[0]
        declarant_analysis_response = openai_client.responses.create(
            model="gpt-4o-mini",
            input=[
                {"role": "system", "content": [{"type": "input_text", "text": classify_declarant_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": f"Deceased person name: {deceased_name}\n\nText:\n\n{declarant_section_text}"}]},
            ],
            text={"format": {"type": "json_object"}},
        )

    declarant_analysis = eval(declarant_analysis_response.output_text)

    # Step 7: Merge both results
    final_result : dict = declarant_analysis | extracted_info

   
    if check_for_text(["police"], declarant_section_text):
        final_result.update({"notary": 0, "undertaker": 0, "hospital": 0, "heir": 0})
        return final_result
    if check_for_text(undertaker_keywords, declarant_section_text):
        final_result["undertaker"] = 1
    if check_for_text(hospital_keywords, declarant_section_text):
        final_result["hospital"] = 1

    return final_result


def process_image_for_ocr(image_path, contrast_factor=1.8, blur_radius=1, threshold=90):
    """
    Processes an image for OCR by enhancing contrast, applying blur, and converting to B&W.

    Args:
        image_path (str): Path to the input image.
        contrast_factor (float): Factor to enhance the contrast. >1 increases contrast, <1 decreases it.
        blur_radius (float): Radius for the Gaussian blur. 0 means no blur.
        threshold (int): Threshold for binarization (0-255). Default is 128.

    Returns:
        PIL.Image.Image: The processed image.
    """
    # Open the image
    pil_image = Image.open(image_path)

    # Enhance the contrast (optional)
    if contrast_factor != 1.0:
        enhancer = ImageEnhance.Contrast(pil_image)
        pil_image = enhancer.enhance(contrast_factor)

    # Convert to RGB if not already in that mode
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")

    # Isolate black pixels: Create a new image with black pixels preserved
    pixels = pil_image.load()
    for y in range(pil_image.height):
        for x in range(pil_image.width):
            r, g, b = pixels[x, y]
            # Keep black pixels; turn others to white
            if not (r < threshold and g < threshold and b < threshold):
                pixels[x, y] = (255, 255, 255)

    # Apply Gaussian blur to the image
    pil_image = pil_image.filter(ImageFilter.GaussianBlur(blur_radius))

    return pil_image


def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        base64_string = base64.b64encode(image_file.read()).decode("utf-8")
    return base64_string


def check_for_text(words, sentence):
    sentence = re.sub(r"\s+", "", unidecode(sentence)).lower()
    for word in words:
        word = re.sub(r"\s+", "", unidecode(word)).lower()
        if word in sentence:
            return True
    return False


def check_for_tesseract():
    os_name = platform.system()
    if os_name == "Windows":
        if os.path.exists("C:/Program Files/Tesseract-OCR"):
            tesseract_path = "C:/Program Files/Tesseract-OCR/tesseract.exe"
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            if "fra" in pytesseract.get_languages():
                return
        else:
            pass
        print("!! tesseract is not installed !!")
        print(
            "Download and install tesseract : https://github.com/UB-Mannheim/tesseract/wiki"
        )
        print("Select French language during installation")
        input()
        sys.exit()
    else:
        try:
            result = subprocess.run(
                ["tesseract", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode == 0:
                if "fra" in pytesseract.get_languages():
                    return
        except FileNotFoundError:
            pass
        print("!! tesseract-fra is not installed !!")
        print('Install tesseract-fra with this command : "brew install tesseract-fra"')
        input()
        sys.exit()


check_for_tesseract()
