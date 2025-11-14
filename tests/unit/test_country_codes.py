"""Tests for country code normalization utilities."""
import pytest
from vpn_sentinel_common.country_codes import (
    normalize_country_code,
    compare_country_codes
)


class TestNormalizeCountryCode:
    """Tests for normalize_country_code function."""
    
    def test_two_letter_code_uppercase(self):
        """Test that 2-letter codes are returned uppercase."""
        assert normalize_country_code("RO") == "RO"
        assert normalize_country_code("ES") == "ES"
        assert normalize_country_code("US") == "US"
    
    def test_two_letter_code_lowercase(self):
        """Test that lowercase 2-letter codes are uppercased."""
        assert normalize_country_code("ro") == "RO"
        assert normalize_country_code("es") == "ES"
        assert normalize_country_code("us") == "US"
    
    def test_full_country_names(self):
        """Test conversion of full country names to codes."""
        assert normalize_country_code("Romania") == "RO"
        assert normalize_country_code("Spain") == "ES"
        assert normalize_country_code("United States") == "US"
        assert normalize_country_code("United Kingdom") == "GB"
        assert normalize_country_code("Bulgaria") == "BG"
    
    def test_case_insensitive_names(self):
        """Test that country names are case-insensitive."""
        assert normalize_country_code("romania") == "RO"
        assert normalize_country_code("ROMANIA") == "RO"
        assert normalize_country_code("RoMaNiA") == "RO"
    
    def test_unknown_values(self):
        """Test that Unknown/empty values are handled."""
        assert normalize_country_code("Unknown") == "Unknown"
        assert normalize_country_code("unknown") == "Unknown"
        assert normalize_country_code("") == "Unknown"
        assert normalize_country_code("   ") == "Unknown"
        assert normalize_country_code(None) == "Unknown"
    
    def test_unrecognized_country(self):
        """Test that unrecognized countries return original."""
        result = normalize_country_code("Atlantis")
        assert result == "Atlantis"


class TestCompareCountryCodes:
    """Tests for compare_country_codes function."""
    
    def test_exact_code_match(self):
        """Test matching with identical codes."""
        assert compare_country_codes("RO", "RO") is True
        assert compare_country_codes("ES", "ES") is True
        assert compare_country_codes("US", "US") is True
    
    def test_name_vs_code_match(self):
        """Test matching full name against code."""
        assert compare_country_codes("Romania", "RO") is True
        assert compare_country_codes("RO", "Romania") is True
        assert compare_country_codes("Spain", "ES") is True
        assert compare_country_codes("United States", "US") is True
    
    def test_case_insensitive_match(self):
        """Test case-insensitive matching."""
        assert compare_country_codes("ro", "RO") is True
        assert compare_country_codes("romania", "RO") is True
        assert compare_country_codes("ROMANIA", "ro") is True
    
    def test_different_countries(self):
        """Test non-matching countries."""
        assert compare_country_codes("RO", "ES") is False
        assert compare_country_codes("Romania", "Spain") is False
        assert compare_country_codes("US", "GB") is False
    
    def test_unknown_values(self):
        """Test that Unknown values return False."""
        assert compare_country_codes("Unknown", "RO") is False
        assert compare_country_codes("RO", "Unknown") is False
        assert compare_country_codes("Unknown", "Unknown") is False
        assert compare_country_codes("", "RO") is False
    
    def test_dns_leak_scenario_false_positive(self):
        """Test the actual bug scenario: Romania vs RO should NOT be leak."""
        # This was the bug: comparing "Romania" != "RO" returned True (leak)
        # After fix, normalized comparison should show they match (no leak)
        assert compare_country_codes("Romania", "RO") is True
        assert compare_country_codes("Bucharest", "RO") is False  # City vs country
    
    def test_real_telegram_messages(self):
        """Test scenarios from actual Telegram messages."""
        # Message 1 & 2: VPN in Romania, DNS in RO -> Should NOT be leak
        assert compare_country_codes("Romania", "RO") is True
        
        # Message 3: VPN in RO, DNS in RO -> Should NOT be leak  
        assert compare_country_codes("RO", "RO") is True
        
        # Message 4: VPN in US, DNS in US -> Should NOT be leak
        assert compare_country_codes("United States", "US") is True
        assert compare_country_codes("US", "US") is True
        
        # Real leak: VPN in Romania, DNS in Germany
        assert compare_country_codes("Romania", "DE") is False
        assert compare_country_codes("RO", "DE") is False
