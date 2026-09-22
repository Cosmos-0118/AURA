"""Lead discovery keeps new matching sites and drops duplicates and weak pages."""

from unittest.mock import patch

from agents.lead_intel import build_lead, discover_candidates, unique_results
from agents.lead_intel import _company_name, _country, _published_email, _published_phone, _requirements, _score, _visible_text


def test_score_comes_from_public_text():
    score, why = _score("jade", "Tomei is a jewellery manufacturer and gold retailer in Malaysia")
    assert score > 40
    assert "jewellery" in why
    assert "gold" in why


def test_empty_page_stays_low():
    score, why = _score("jaguar", "Welcome to our summer photo blog")
    assert score == 20
    assert "did not mention" in why


def test_title_and_country_are_read_from_html():
    html = """
    <html><head>
      <title>Habib Jewels | Malaysia</title>
      <meta name="description" content="Gold jewellery retailer in Kuala Lumpur">
    </head><body><p>Showrooms across Malaysia</p></body></html>
    """
    title, description, text = _visible_text(html)
    assert _company_name(title, "https://www.habibjewels.com/") == "Habib Jewels"
    assert "Gold jewellery" in description
    assert _country(f"{title} {text}", "Malaysia") == "Malaysia"


def test_public_contact_and_requirements_are_read_from_the_page():
    html = """
    <html><body>
      <a href="mailto:customerservice@habibjewels.com">Email</a>
      <a href="tel:+60192222916">Call</a>
      <p>Habib operates jewellery showrooms and gold retail across Malaysia.</p>
    </body></html>
    """
    assert _published_email(html) == "customerservice@habibjewels.com"
    assert "+60192222916" in (_published_phone(html) or "")
    _, _, text = _visible_text(html)
    requirements = _requirements("jade", "", text)
    assert "jewellery" in requirements.lower()


def test_duplicate_company_domain_is_kept_once():
    results = unique_results(
        [
            {"url": "https://example.com/about", "title": "Example", "snippet": "Jewellery retailer"},
            {"url": "https://www.example.com/contact", "title": "Example contact", "snippet": "Gold"},
            {"url": "https://en.wikipedia.org/wiki/Jewellery", "title": "Jewellery", "snippet": "Wiki"},
        ]
    )
    assert len(results) == 1
    assert results[0]["url"] == "https://example.com/about"


def test_linkedin_posts_are_not_collapsed_to_one_domain():
    results = unique_results(
        [
            {"url": "https://www.linkedin.com/posts/one", "title": "One", "snippet": "Watch retailer"},
            {"url": "https://www.linkedin.com/posts/two", "title": "Two", "snippet": "Jewellery"},
        ]
    )
    assert len(results) == 2


def test_page_without_brand_keywords_is_dropped():
    lead = build_lead(
        "jade",
        "https://example.com",
        "Summer picnic",
        "A blog about weekends",
        {"title": "Summer picnic", "description": "", "text": "Bring a blanket", "company_url": "https://example.com"},
    )
    assert lead is None


def test_new_domain_with_brand_keywords_is_kept():
    lead = build_lead(
        "jade",
        "https://newjeweller.example",
        "Northwind Jewellers",
        "Wholesale jewellery manufacturer",
        {
            "title": "Northwind Jewellers",
            "description": "Gold and diamond jewellery",
            "text": "We manufacture jewellery for retailers.",
            "email": "info@newjeweller.example",
            "phone": "+1 202 555 0147",
            "company_url": "https://newjeweller.example",
        },
        "US",
    )
    assert lead is not None
    assert lead["url"] == "https://newjeweller.example"
    assert lead["email"] == "info@newjeweller.example"
    assert lead["fit_score"] > 20
    assert lead["source_url"] == "https://newjeweller.example"


def test_discovery_keeps_a_new_domain_from_search_results():
    def fake_search(query, purpose, location, domain_type):
        if location == "US" and "jewellery manufacturer" in query:
            return [
                {
                    "url": "https://newjeweller.example",
                    "title": "Northwind Jewellers",
                    "snippet": "Wholesale jewellery manufacturer",
                }
            ]
        return []

    with patch("agents.lead_intel.search_web", side_effect=fake_search), patch("agents.lead_intel.time.sleep"):
        found, _errors = discover_candidates()
    assert any(item["url"] == "https://newjeweller.example" for item in found)
