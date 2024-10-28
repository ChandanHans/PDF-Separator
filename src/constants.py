import json
import os
from dotenv import load_dotenv

from .utils import resource_path


load_dotenv(dotenv_path=resource_path(".env"))

GPT_KEY = os.environ["GPT_KEY"]
INPUT_FOLDER = "./Input"
OTHER_OUTPUT_FOLDER = "./Other"
NOTARY_OUTPUT_FOLDER = "./Notary"
UNDERTAKER_OUTPUT_FOLDER = "./Undertaker"
IMAGE_FOLDER = "./images"
COMPLETED_FOLDER = "./Completed"