import json
import os
from dotenv import load_dotenv

from .utils import resource_path


load_dotenv(dotenv_path=resource_path(".env"))

GPT_KEY_1 = os.environ["GPT_KEY_1"]
GPT_KEY_2 = os.environ["GPT_KEY_2"]
CREDS_JSON = json.loads(os.environ["CREDS_JSON"])
LETTER_TEMPLATE = resource_path("templates/letter_template.docx")
IMAGE_SHEET_ID = '1e4GzXCftJYFRbh3xKWnvRK8zE-FjOUut7FinhFj-2ug'
ANNUAIRE_HERITIERS_SHEET_ID = "1W0CIhX7QPwP-zYQfu3cnHbZxwsb3MVqZwVrgAelS0iU"
ANNUAIRE_TOWNHALL_SHEET_ID = "19uljibwPpsUoFU5nBPWEmj4UPl3RPR4VXCCa9RVJz84"
ANNUAIRE_NOTAIRES_SHEET_ID = "1NBWDbmuXHKr6yWsEvxJhio4uaUPKol6_dJvtgKJCDhc"
ANNUAIRE_HOSPITAL_SHEET_ID = "1el7A2yt0ABkRQu9RzCojoy_hY_Fuq8cz3gKsMmWc2no"
DEATH_CERTIFICATES_FOLDER_ID = '16r80-Mq5jDo6Lj9svu0hD7ULYMyyUnHp'
NORMAL_INPUT_FOLDER = "./Normal-Input"
HANDWRITTEN_INPUT_FOLDER = "./Handwritten-Input"
OUTPUT_FOLDER = "./Output"
IMAGE_FOLDER = "./Images"
COMPLETED_FOLDER = "./Completed"
TEMP_LETTER_FOLDER = "./Temp-Letter"
LETTER_FOLDER = "./Letter"
TOKEN_FILE = 'token.pickle'
UNDERTAKER_FOLDER_ID = "149xu_E_zWx6cfIekpq-gpf4g0aHY3avr"
