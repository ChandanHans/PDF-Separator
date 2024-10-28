import os
import platform
import subprocess
import pytesseract
from openai import OpenAI

from .constants import *
from .utils import *


openai_client = OpenAI(api_key=GPT_KEY)


def get_image_result(image_path):
    text = pytesseract.image_to_string(image_path, lang="fra")
    prompt = (
        "Text:\n"
        + text
        + """


1. Filter unnecessary characters like (*, #, ~, etc.)
2. for 1st option:
    - if date of death before 2019 then 1 else 0
3. for 2nd and 3rd:
    - If the word present 1.
    - If not present 0.
- Return the result in the exact JSON format.

Please format the output as a JSON object, following this structure exactly:
{
    "date of death before 2019": (if True 1 else 0) 0/1,
    "Acte de notoriété": (Word with : notoriété then 1) (Note: if mentions marginales is Neant then 0) 0/1.
    "pompe funèbre" : (Word with : attaché funéraire / Pompes funèbres / Conseiller Funéraire / Conseillère Funéraire / gérant de pompes funèbres /  gérante de pompes funèbres/ thanatopracteur / démarcheur  /démarcheuse / assistante funéraire / assistant funéraire / chef d'agence / Agent funéraire / Directeur etc) 0/1.

}
""")
    
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
