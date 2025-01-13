"""Value objects for EarnORM."""

from enum import Enum


class Country(str, Enum):
    """Country codes for phone number validation."""

    INTERNATIONAL = ""  # Default international format
    VN = "VN"  # Vietnam
    US = "US"  # United States
    GB = "GB"  # United Kingdom
    SG = "SG"  # Singapore
    JP = "JP"  # Japan
    KR = "KR"  # South Korea
    CN = "CN"  # China

    @property
    def code(self) -> str:
        """Get country calling code."""
        codes = {
            "VN": "+84",
            "US": "+1",
            "GB": "+44",
            "SG": "+65",
            "JP": "+81",
            "KR": "+82",
            "CN": "+86",
        }
        return codes.get(self.value, "")

    @property
    def name(self) -> str:
        """Get country name."""
        names = {
            "VN": "Vietnam",
            "US": "United States",
            "GB": "United Kingdom",
            "SG": "Singapore",
            "JP": "Japan",
            "KR": "South Korea",
            "CN": "China",
        }
        return names.get(self.value, "International")
