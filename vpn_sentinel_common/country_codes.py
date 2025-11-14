"""Country code normalization utilities for VPN Sentinel.

This module provides utilities to normalize country codes to 2-letter ISO format.
Handles cases where geolocation services return full country names or inconsistent formats.
"""

# Mapping of common country names to ISO 3166-1 alpha-2 codes
COUNTRY_NAME_TO_CODE = {
    # Europe
    "romania": "RO",
    "spain": "ES",
    "bulgaria": "BG",
    "germany": "DE",
    "france": "FR",
    "italy": "IT",
    "united kingdom": "GB",
    "uk": "GB",
    "netherlands": "NL",
    "poland": "PL",
    "portugal": "PT",
    "sweden": "SE",
    "norway": "NO",
    "denmark": "DK",
    "finland": "FI",
    "austria": "AT",
    "belgium": "BE",
    "switzerland": "CH",
    "czechia": "CZ",
    "czech republic": "CZ",
    "hungary": "HU",
    "ireland": "IE",
    "greece": "GR",
    
    # Americas
    "united states": "US",
    "usa": "US",
    "canada": "CA",
    "mexico": "MX",
    "brazil": "BR",
    "argentina": "AR",
    "chile": "CL",
    "colombia": "CO",
    
    # Asia Pacific
    "japan": "JP",
    "australia": "AU",
    "singapore": "SG",
    "india": "IN",
    "south korea": "KR",
    "china": "CN",
    "hong kong": "HK",
    "taiwan": "TW",
    "thailand": "TH",
    "vietnam": "VN",
    "indonesia": "ID",
    "malaysia": "MY",
    "philippines": "PH",
    "new zealand": "NZ",
    
    # Middle East
    "israel": "IL",
    "united arab emirates": "AE",
    "uae": "AE",
    "saudi arabia": "SA",
    "turkey": "TR",
    
    # Africa
    "south africa": "ZA",
    "egypt": "EG",
}


def normalize_country_code(country: str) -> str:
    """Normalize country string to 2-letter ISO code.
    
    Args:
        country: Country string (can be full name, 2-letter code, or unknown)
    
    Returns:
        2-letter ISO country code in uppercase, or original string if:
        - Already a 2-letter code
        - "Unknown" or similar
        - Not recognized
    
    Examples:
        >>> normalize_country_code("Romania")
        "RO"
        >>> normalize_country_code("RO")
        "RO"
        >>> normalize_country_code("United States")
        "US"
        >>> normalize_country_code("Unknown")
        "Unknown"
    """
    if not country or not isinstance(country, str):
        return "Unknown"
    
    # Strip and handle empty/unknown cases
    country_clean = country.strip()
    if not country_clean or country_clean.lower() in ("unknown", "n/a", "none"):
        return "Unknown"
    
    # If already a 2-letter code, return uppercase
    if len(country_clean) == 2 and country_clean.isalpha():
        return country_clean.upper()
    
    # Try to look up full name
    country_lower = country_clean.lower()
    if country_lower in COUNTRY_NAME_TO_CODE:
        return COUNTRY_NAME_TO_CODE[country_lower]
    
    # Return original if not recognized (keep consistent format)
    return country_clean


def compare_country_codes(country1: str, country2: str) -> bool:
    """Compare two country codes/names for equality.
    
    Args:
        country1: First country (code or name)
        country2: Second country (code or name)
    
    Returns:
        True if countries match (after normalization), False otherwise
    
    Examples:
        >>> compare_country_codes("Romania", "RO")
        True
        >>> compare_country_codes("RO", "RO")
        True
        >>> compare_country_codes("ES", "Spain")
        True
        >>> compare_country_codes("US", "RO")
        False
    """
    norm1 = normalize_country_code(country1)
    norm2 = normalize_country_code(country2)
    
    # If either is Unknown, cannot definitively compare
    if norm1 == "Unknown" or norm2 == "Unknown":
        return False
    
    return norm1 == norm2
