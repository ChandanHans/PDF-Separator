from unidecode import unidecode
from src.constants import *
from src.utils import *
import pandas as pd


def get_undertaker_data(sheets_service):
    request = sheets_service.spreadsheets().values().get(
        spreadsheetId=ANNUAIRE_UNDERTAKER_SHEET_ID,
        range="PF Annuaire!A:D", 
    )
    result = execute_with_retry(request)
    sheet_data = result.get("values", [])

    if not sheet_data:
        return []

    header = sheet_data[0]
    result_list = []

    # Normalize rows: skip if too short, trim if too long
    normalized_rows = []
    for row in sheet_data[1:]:
        if len(row) < len(header):
            continue  # Skip incomplete row
        normalized_rows.append(row[:len(header)])  # Trim extra columns if any

    df = pd.DataFrame(normalized_rows, columns=header)

    for _, row in df.iterrows():
        declarant = unidecode(row["Déclarant"]).replace(" ", "").replace("-", "").replace(",", "").lower()
        result_list.append(declarant)

    return result_list
