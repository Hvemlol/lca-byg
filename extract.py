import instructor
import pdfplumber
from openai import OpenAI

from models import EPDRecord
from settings import get_api_key

SYSTEM_PROMPT = (
    "You extract structured data from Environmental Product Declarations (EPDs) "
    "for construction products. Extract only values explicitly stated in the text. "
    "Use null for fields that are absent. Normalize numbers to plain floats "
    "(kg CO2-eq per declared unit). Do not invent values."
)

USER_PROMPT = """Extract the EPD information from the text below.

Pay attention to:
- declared/functional unit (often stated as "declared unit" or "functional unit")
- GWP (global warming potential / climate change) for modules A1-A3 and, if stated, A1-C4 total
- EPD registration number and publication year
- manufacturer name and country
- validity period (typically 5 years from publication)

EPD text:
{text}
"""

MAX_TEXT_CHARS = 80_000


def extract_text_from_pdf(pdf_path: str) -> str:
    chunks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            chunks.append(page.extract_text() or "")
    text = "\n".join(chunks).strip()
    if not text:
        raise ValueError(f"No extractable text found in {pdf_path} (scanned PDF?)")
    return text[:MAX_TEXT_CHARS]


def extract_epd_record(text: str, model: str = "gpt-4o-mini") -> EPDRecord:
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "No API key configured. Set it in the app (Settings) or via the "
            "OPENAI_API_KEY environment variable."
        )
    client = instructor.from_openai(OpenAI(api_key=api_key))
    return client.chat.completions.create(
        model=model,
        response_model=EPDRecord,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT.format(text=text)},
        ],
    )
