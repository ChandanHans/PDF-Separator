import json
import os
from dotenv import load_dotenv

from .utils import resource_path


load_dotenv(dotenv_path=resource_path(".env"))

GPT_KEY = os.environ["GPT_KEY"]
CREDS_JSON = json.loads(os.environ["CREDS_JSON"])
LETTER_TEMPLATE = resource_path("templates/letter_template.docx")
IMAGE_SHEET_ID = '1e4GzXCftJYFRbh3xKWnvRK8zE-FjOUut7FinhFj-2ug'
ANNUAIRE_HERITIERS_SHEET_ID = "1W0CIhX7QPwP-zYQfu3cnHbZxwsb3MVqZwVrgAelS0iU"
ANNUAIRE_TOWNHALL_SHEET_ID = "19uljibwPpsUoFU5nBPWEmj4UPl3RPR4VXCCa9RVJz84"
ANNUAIRE_NOTAIRES_SHEET_ID = "1NBWDbmuXHKr6yWsEvxJhio4uaUPKol6_dJvtgKJCDhc"
DEATH_CERTIFICATES_FOLDER_ID = '16r80-Mq5jDo6Lj9svu0hD7ULYMyyUnHp'
INPUT_FOLDER = "./Input"
OTHER_OUTPUT_FOLDER = "./Other"
HEIR_OUTPUT_FOLDER = "./Heir"
NOTARY_OUTPUT_FOLDER = "./Notary"
UNDERTAKER_OUTPUT_FOLDER = "./Undertaker"
IMAGE_FOLDER = "./Images"
COMPLETED_FOLDER = "./Completed"
TEMP_LETTER_FOLDER = "./Temp-Letter"
LETTER_FOLDER = "./Letter"
TOKEN_FILE = 'token.pickle'