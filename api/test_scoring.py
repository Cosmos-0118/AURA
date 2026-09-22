import pytest
from agents.leads import calculate_fit_score

def test_calculate_fit_score_high_fit():
    lead_data = {
        "url": "https://example.com",
        "phone": "+1234567890",
        "public_email": "hello@example.com",
        "location": "Singapore 12345",
        "category": "Jewellery",
        "social_links": ["https://instagram.com/example"],
        "services": ["Custom jewelry design"]
    }
    
    score, reasons = calculate_fit_score(lead_data, target_category="Jewellery", target_location="Singapore")
    
    # URL(15) + Phone(10) + Email(15) + Location(20) + Category(25) + Social(15) = 100
    assert score == 100
    assert len(reasons) == 6

def test_calculate_fit_score_low_fit():
    lead_data = {
        "location": "Jakarta, Indonesia",
        "category": "Bakery",
    }
    
    score, reasons = calculate_fit_score(lead_data, target_category="Jewellery", target_location="Singapore")
    
    # Missing all matches
    assert score == 0
    assert len(reasons) == 0

def test_calculate_fit_score_partial_fit():
    lead_data = {
        "url": "https://example.com",
        "location": "Singapore",
        "category": "Retail",
        "services": ["Jewellery repair"]
    }
    
    score, reasons = calculate_fit_score(lead_data, target_category="Jewellery", target_location="Singapore")
    
    # URL(15) + Location(20) + ServiceMatch(15) = 50
    assert score == 50
    assert any("services" in r.lower() for r in reasons)
