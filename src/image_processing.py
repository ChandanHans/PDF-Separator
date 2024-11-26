import os
import platform
import subprocess
import pytesseract
from openai import OpenAI
from unidecode import unidecode
from googleapiclient.http import MediaFileUpload

from .constants import *
from .utils import *




def clean_name_for_comparison(name: str):
    """Clean the name by removing spaces, commas, and dashes."""
    return unidecode(name).replace(" ", "").replace(",", "").replace("-", "").lower()


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
    request = drive_service.files().create(body=file_metadata, media_body=media, fields="id, webViewLink")
    uploaded_file = execute_with_retry(request)
    # Get the file ID and web link
    file_link = uploaded_file.get("webViewLink")

    # Append the image name and link to the Google Sheet
    row_data = [file_name, file_link]
    request = sheets_service.spreadsheets().values().append(
        spreadsheetId=IMAGE_SHEET_ID,
        range="Sheet1!A:B",
        valueInputOption="RAW",
        body={"values": [row_data]},
    )
    execute_with_retry(request)
    existing_images.append(row_data)
    return file_link

openai_client = OpenAI(api_key=GPT_KEY)


def get_image_result(image_path):
    text = pytesseract.image_to_string(image_path, lang="fra")
    prompt = (
        "Text:\n"
        + text
        + """
Task Requirements:

1. Filter Unnecessary Characters
    - Remove characters like (*, #, ~, etc.).

2. Case Sensitivity  
    - Don't change any case because I Identify fname and lname with case.

3. Logic for Key Fields

    - For "Date of death before 2016":
        - Return 1 if the date of death is before 2016; otherwise, return 0.
    - For "Acte de notoriété":
        - Return 1 if the word notoriété is found in the text.
        - If "mentions marginales" contains the word Neant, return 0.
    - For "Pompe funèbre":
        - Return 1 if any of the following keywords are found:
            attaché funéraire, Pompes funèbres, Conseiller Funéraire, Conseillère Funéraire,
            gérant de pompes funèbres, gérante de pompes funèbres, thanatopracteur,
            démarcheur, démarcheuse, assistante funéraire, assistant funéraire,
            chef d'agence, Agent funéraire, Directeur, Graveur, Marbrier,
            Cadre en Pompes Funebres, etc.
        - Otherwise, return 0.
        
4. Extract Information About the Deceased Person
    - For "Deceased person full name": 
        - Extract from the beginning of the text.
    - For "Date of Death": 
        - Format as dd/mm/yyyy.
    - For "City of death": 
        - Extract the city name.
    - For "Relative Name": 
        - Extract from delaration section.
        - Extract the name of the relative.
        - not the relationship.
        - if there no relative name in delaration section then "".
        - hints : search for word like (fils, fille, père, mère, frère, sœur, cousin, cousine, neveu, nièce, oncle, tante, Epoux, Epouse, petits fils, petite fille, compagne, compagnon, concubin, concubine, ex-époux, ex-épouse, ex-mari, ex-femme, ami, amie, etc...) in delaration section.
    - For "Relative Address": 
        - Extract the full address from the declaration section.
    - For "Relation with Deceased person": 
        - Extract from delaration section
        - Extract the relation of the Relative.
        - e.g., fils, fille, père, mère, frère, sœur, cousin, cousine, neveu, nièce, oncle, tante, Epoux, Epouse, petits fils, petite fille, compagne, compagnon, concubin, concubine, ex-époux, ex-épouse, ex-mari, ex-femme, ami, amie, etc...
    - For "Name of spouse": 
        - Search before delaration section.
        - Extract the name of the spouse.
        - hints : search for word like (époux, épouse, concubin, concubine, mari, femme, pacsé etc.) before delaration section.

Output Format:
Return the results as a JSON object, strictly adhering to this structure:

json
{
    "Date of death before 2016": 0/1,
    "Acte de notoriété": 0/1,
    "Pompe funèbre": 0/1,
    "About Deceased Person": {
        "Deceased person full name": "",
        "Date of Death": "dd/mm/yyyy",
        "City of death": "",
        "Relative Name": "",
        "Relative Address": "",
        "Relation with Deceased person": "",
        "Name of spouse": ""
    }
}
    """
)
    
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": prompt,
            },
        ],
        response_format={"type": "json_object"}
    )
    result = eval(response.choices[0].message.content)
    return result


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
