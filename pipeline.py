from pathlib import Path

from db import get_connection, insert_epd
from extract import extract_epd_record, extract_text_from_pdf
from models import EPDRecord


def extract_pdf(pdf_path: str, model: str = "gpt-4o-mini") -> EPDRecord:
    text = extract_text_from_pdf(pdf_path)
    record = extract_epd_record(text, model=model)
    record.source_file = Path(pdf_path).name
    return record


def process_pdf(pdf_path: str, db_path: str = "lca.db", model: str = "gpt-4o-mini") -> EPDRecord:
    record = extract_pdf(pdf_path, model=model)
    conn = get_connection(db_path)
    try:
        insert_epd(conn, record)
    finally:
        conn.close()
    return record
