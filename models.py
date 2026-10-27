from typing import Optional

from pydantic import BaseModel, Field


class EPDRecord(BaseModel):
    epd_number: Optional[str] = Field(None, description="EPD registration number, e.g. EPD-Norge or IBU format")
    product_name: str = Field(description="Product name as stated in the EPD")
    manufacturer: Optional[str] = None
    declared_unit: str = Field(description="Functional/declared unit, e.g. '1 m3', '1 kg', '1 piece'")
    gwp_a1_a3: Optional[float] = Field(None, description="Global warming potential, modules A1-A3, kg CO2-eq per declared unit")
    gwp_total: Optional[float] = Field(None, description="Global warming potential, total (A1-C4), kg CO2-eq per declared unit")
    pdf_year: Optional[int] = Field(None, description="Publication year of the EPD document")
    valid_until: Optional[str] = Field(None, description="Validity end date, ISO format YYYY-MM-DD if stated")
    country: Optional[str] = Field(None, description="Country of manufacturer or EPD programme operator")
    source_file: Optional[str] = None
