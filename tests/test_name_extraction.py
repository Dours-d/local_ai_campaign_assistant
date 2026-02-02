
import pytest
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from utils.normalize_campaigns import extract_names_from_title

def test_extract_names_standard_patterns():
    """Test standard "Help X" patterns."""
    # Basic chuffed pattern
    result = extract_names_from_title("Help Mohammed Yasser and his family rebuild their lives in Gaza, Palestine.")
    assert result["display_name"] == "Mohammed Y."
    assert result["first_name"] == "Mohammed"
    
    # Another common pattern
    result = extract_names_from_title("Help Fares and his family rebuild their lives")
    assert result["display_name"] == "Fares"
    assert result["first_name"] == "Fares"

def test_extract_names_incorrect_stopwords():
    """Test that stopwords like 'Help', 'Support' are NOT extracted as names."""
    # This was a failing case: "Help M."
    result = extract_names_from_title("Help Mohammed K. and his family rebuild their lives")
    assert result["first_name"] == "Mohammed"
    assert result["display_name"] == "Mohammed K." 
    
    # "Support" case
    result = extract_names_from_title("Support the Gaza evacuation of the Al-Masri family")
    assert result["first_name"] != "Support"
    assert "Al-Masri" in result["full_name"] or "Al-Masri" in result["display_name"]

def test_extract_names_arabic_transliteration():
    """Test names with common transliteration patterns."""
    result = extract_names_from_title("Help Abdallah and his family go out of Gaza")
    assert result["first_name"] == "Abdallah"
    
def test_extract_names_complex_titles():
    """Test more complex titles where name isn't immediately at start."""
    # Case where "Emergency" or similar might be at start
    result = extract_names_from_title("Urgent: Help Ahmed and his children survive")
    assert result["first_name"] == "Ahmed"

def test_fallback_behavior():
    """Test when no clear pattern matches."""
    result = extract_names_from_title("Gaza Resilience Project Fundraiser")
    # Should default to something reasonable or Anonymous/Family
    assert result["display_name"] != "Gaza" # Should not just pick first capitalized word if it's a place

if __name__ == "__main__":
    # fast manual run
    for func in [test_extract_names_standard_patterns, test_extract_names_incorrect_stopwords, test_extract_names_arabic_transliteration]:
        try:
            func()
            print(f"✅ {func.__name__} passed")
        except AssertionError as e:
            print(f"❌ {func.__name__} failed: {e}")
            try:
                # Re-run to print result for debugging
                if func.__name__ == "test_extract_names_incorrect_stopwords":
                    from utils.normalize_campaigns import extract_names_from_title
                    print("   Debug: 'Support...' ->", extract_names_from_title("Support the Gaza evacuation of the Al-Masri family"))
            except:
                pass
        except Exception as e:
            print(f"❌ {func.__name__} raised error: {e}")
