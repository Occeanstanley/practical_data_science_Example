import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
import pandas as pd

# Function to check domain trust based on predefined list
def get_domain_trust(domain):
    trusted_domains = ["mayoclinic.org", "cdc.gov", "who.int", "nih.gov", "healthline.com"]
    if domain in trusted_domains:
        return 9  # High trust
    elif domain.endswith(".gov") or domain.endswith(".edu"):
        return 10
    elif domain.endswith(".org") or domain.endswith(".com"):
        return 7
    else:
        return 4  # Low trust

# Function to check HTTPS security
def check_https(url):
    return 5 if url.startswith("https") else 0

# Function to fetch webpage content
def fetch_page_content(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException:
        return None

# Function to check content relevance
def check_content_relevance(content, keywords):
    if not content:
        return 0

    soup = BeautifulSoup(content, "html.parser")
    title = soup.title.string if soup.title else ""
    meta_desc = soup.find("meta", attrs={"name": "description"})
    meta_desc = meta_desc["content"] if meta_desc else ""

    text = title.lower() + " " + meta_desc.lower()
    relevance_score = sum(1 for word in keywords if word in text)
    
    return min(relevance_score * 2, 10)  # Scale up to 10

# Function to check fast-check score
def check_fast_check_score(content):
    return 8 if content else 4  # Placeholder for actual fact-checking implementation

# Function to check bias score (Placeholder logic)
def check_bias_score(domain):
    unbiased_sources = ["who.int", "cdc.gov", "nih.gov"]
    if domain in unbiased_sources:
        return 10
    return 5  # Default medium bias

# Function to check citation score
def check_citation_score(content):
    if not content:
        return 0

    soup = BeautifulSoup(content, "html.parser")
    external_links = [a["href"] for a in soup.find_all("a", href=True) if "http" in a["href"]]

    if len(external_links) >= 5:
        return 10
    elif len(external_links) >= 3:
        return 7
    elif len(external_links) >= 1:
        return 5
    else:
        return 2

# Main function to evaluate URL validity
def evaluate_url(url, keywords):
    content = fetch_page_content(url)
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.replace("www.", "")

    scores = {
        "Domain Trust": get_domain_trust(domain),
        "Content Relevance": check_content_relevance(content, keywords),
        "Fast-Check Score": check_fast_check_score(content),
        "Bias Score": check_bias_score(domain),
        "Citation Score": check_citation_score(content),
        "Security (HTTPS)": check_https(url)
    }

    total_score = sum(scores.values())
    final_validity_score = (total_score / 55) * 100  # Normalize to 0-100
    scores["Final Validity Score"] = round(final_validity_score, 2)

    return {"URL": url, "Scores": scores}

# Example URL evaluation
test_url = "https://www.mayoclinic.org/healthy-lifestyle/infant-and-toddler-health/expert-answers/air-travel-with-infant/faq-20058539"
keywords = ["newborn", "health", "flight", "risks", "air travel", "infant"]
result = evaluate_url(test_url, keywords)

# Display results
df = pd.DataFrame([result["Scores"]])

# Print results to console
print(df)

# Save results to CSV
df.to_csv("url_validity_results.csv", index=False)
