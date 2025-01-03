import os
import platform
import subprocess
import pytesseract
from openai import OpenAI
from unidecode import unidecode
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageEnhance, ImageFilter

from .constants import *
from .utils import *


def clean_name_for_comparison(name: str):
    """Clean the name by removing spaces, commas, and dashes."""
    return unidecode(name).replace(" ", "").replace(",", "").replace("-", "")


def upload_image_and_append_sheet(
    name, image_path, drive_service, sheets_service, existing_images=None
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
    row_data = [file_name, file_link]
    request = (
        sheets_service.spreadsheets()
        .values()
        .append(
            spreadsheetId=IMAGE_SHEET_ID,
            range="Sheet1!A:B",
            valueInputOption="RAW",
            body={"values": [row_data]},
        )
    )
    execute_with_retry(request)
    existing_images.append(row_data)
    return file_link


openai_client = OpenAI(api_key=GPT_KEY)


def get_image_result(image_path):
    image = process_image_for_ocr(image_path)
    text: str = pytesseract.image_to_string(image, lang="fra", config='--oem 3 --psm 6')
    prompt1 = (
        "Text:\n"
        + text
        + """
Task Requirements:

1. Filter Unnecessary Characters
    - Remove characters like (*, #, ~, etc.).

2. Case Sensitivity  
    - Don't change any case because I Identify fname and lname with case.

3. Logic for Key Fields
    - for "Address is under Paris":
        - Return 1 if the Deceased person person is under Paris (Department 75).
        - Otherwise, return 0.
            
4. Extract Information About the Deceased Person
    - For "Deceased person full name": 
        - Extract from the beginning of the text.
    - For "Date of Death": 
        - Format as dd/mm/yyyy.
    - For "City":
        - City of the Deceased person. (only City) (domicile, domicilié, domiciliée, habitant, demeurant, etc...)
    - For "Department Number":
        - Department Number of City of the Deceased person.
    - For "City of death": 
        - Extract the city name of death.
    - For "Relative Name": 
        - Extract from Déclarant section.
        - Extract the name of the relative.
        - not the relationship.
        - if there no relative name in Déclarant section then "".
        - hints : search for word like (fils, fille, père, mère, frère, sœur, cousin, cousine, neveu, nièce, oncle, tante, Epoux, Epouse, petits fils, petite fille, compagne, compagnon, concubin, concubine, ex-époux, ex-épouse, ex-mari, ex-femme, ami, amie, etc...) in Déclarant section.
    - For "Relative Address": 
        - Extract Address from the full address from the declaration section.
    - For "Relative City": 
        - Extract only City of full address from the declaration section.
    - For "Relative Address Zip code":
        - Return the Zip code of Relative Address.
        - It may not be in the Text but return it yourself
    - For "Relation with Deceased person": 
        - Extract from Déclarant section
        - Extract the relation of the Relative.
        - e.g., fils, fille, père, mère, frère, sœur, cousin, cousine, neveu, nièce, oncle, tante, Epoux, Epouse, petits fils, petite fille, compagne, compagnon, concubin, concubine, ex-époux, ex-épouse, ex-mari, ex-femme, ami, amie, etc...
    - For "Name of spouse": 
        - Search before Déclarant section.
        - Extract the name of the spouse.
        - hints : search for word like (époux, épouse, concubin, concubine, mari, femme, pacsé etc.) before Déclarant section.
        - skip divorce info.

Output Format:
Return the results as a JSON object, strictly adhering to this structure:

json
{
    "Address is under Paris" : 0/1,
    "About Deceased Person": {
        "Deceased person full name": "",
        "Date of Death": "dd/mm/yyyy",
        "City": "",
        "Department Number": "",
        "City of death": "",
        "Relative Full Name": "",
        "Relative Address": "",
        "Relative City": "",
        "Relative Address Zip code":"",
        "Relation with Deceased person": "",
        "Name of spouse": ""
    }
}
    """
    )

    response1 = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": prompt1,
            },
        ],
        response_format={"type": "json_object"},
    )
    result1 = eval(response1.choices[0].message.content)

    a = unidecode(text).lower().split("clarant",1)
    b = unidecode(text).lower().split("claration",1)
    text2 = a[1] if len(a)>1 else b[1] if len(b)>1 else text
    print(text2)
    prompt2 = f'Deceased person name : {list(list(result1.values())[1].values())[0]}\n\n Text:\n\n ""'+ text2 + """""
        
    - For "word 1":
        - Return 1 if the word "Acte de notoriété" / "notoriete" is found in the text.
        - Note: If there is "mentions marginales" and contains the word Neant then return 0.
    - For "word 2":
        - Return 1 if any of the following keywords are found:
            (Funéraire, Assistant funéraire / Assistante funéraire, Chef d'entreprise / Cheffe d'entreprise, Conseiller Funéraire / Conseillère Funéraire, Conservateur du Cimetière / Conservatrice du Cimetière, Conservateur du cimetière, Chef d'entreprise de Pompes Funèbres / Cheffe d'entreprise de Pompes Funèbres, Services Funéraires, Employé PF / Employée PF, Employé Pompes Funèbres / Employée Pompes Funèbres, Dirigeant de PF / Dirigeante de PF, Dirigeant de Pompes Funèbres / Dirigeante de Pompes Funèbres, Gérant de Société / Gérante de Société, Gérant de la société / Gérante de la société, Gérant / Gérante, Directeur d'agence / Directrice d'agence, Responsable des services, Responsable d'agence, Porteur funéraire, Pompes Funèbres, Pompe Funèbre, Opérateur Funéraire / Opératrice Funéraire, etc...)
        - Search only in Déclarant section.
        - Otherwise, return 0.
    - for "word 3":
        - It is to check wheather a relative info of Deceased person exist in the text or not.
        - Analyze text properly. Don't return 1 for someone from the hospital or the police or an official from the Townhall or there relative.
        - Hints : search for word fils, fille, père, mère, frère, sœur, cousin, cousine, neveu, nièce, oncle, tante, epoux, epouse, petits fils, petite fille, compagne, compagnon, concubin, concubine, ex-époux, ex-épouse, ex-mari, ex-femme, ami or amie.
        - Return 1 if any of the word exist in the text.
        - Or Return 1 if there any relative of Deceased person name like same last name.
        - Search only in Déclarant section.
        - Otherwise, return 0.
        
return json:
{
    "word 1": 0/1,
    "word 2": 0/1,
    "word 3": 0/1,
}
"""
    response2 = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": prompt2,
            },
        ],
        response_format={"type": "json_object"},
    )
    result2 = eval(response2.choices[0].message.content)

    result = result2 | result1

    list1 = ["Funéraire", "Assistant funéraire", "Assistante funéraire", "Chef d'entreprise", "Cheffe d'entreprise", "Conseiller Funéraire", "Conseillère Funéraire", "Conservateur du Cimetière", "Conservatrice du Cimetière", "Conservateur du cimetière", "Chef d'entreprise de Pompes Funèbres", "Cheffe d'entreprise de Pompes Funèbres", "Services Funéraires", "Employé PF", "Employée PF", "Employé Pompes Funèbres", "Employée Pompes Funèbres", "Dirigeant de PF" , "Dirigeante de PF", "Dirigeant de Pompes Funèbres" , "Dirigeante de Pompes Funèbres", "Gérant de Société" , "Gérante de Société", "Gérant de la société" , "Gérante de la société", "Gérant" , "Gérante", "Directeur d'agence", "Directrice d'agence", "Responsable des services", "Responsable d'agence", "Porteur funéraire", "Pompes Funèbres", "Pompe Funèbre", "Opérateur Funéraire", "Opératrice Funéraire", "chauffeur porteur"]
    
    if check_for_text(["notoriete"], text2):
        result["word 1"] = 1
    if check_for_text(list1, text2):
        result["word 2"] = 1
        
    return result

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
    if pil_image.mode != 'RGB':
        pil_image = pil_image.convert('RGB')

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

def check_for_text(words, sentence):
    sentence = re.sub(r'\s+', '', unidecode(sentence)).lower()
    for word in words:
        word = re.sub(r'\s+', '', unidecode(word)).lower()
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
