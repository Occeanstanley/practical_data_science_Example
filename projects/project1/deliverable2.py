import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
import pandas as pd
import spacy
import os
from google.colab import userdata
from transformers import pipeline

# Load API keys securely from Google Colab Secrets
HF_TOKEN = userdata.get("HF_TOKEN") or os.getenv("HF_TOKEN")  # Retrieve Hugging Face Token
SERP_API_KEY = userdata.get("SERPAPI_API_KEY") or os.getenv("SERPAPI_API_KEY")  # Retrieve SERP API Key

SERP_API_URL = "https://serpapi.com/search"

# Check if HF_TOKEN is retrieved
if HF_TOKEN is None:
    print("⚠️ Warning: Hugging Face Token (HF_TOKEN) not found. Please check Google Colab Secrets!")

# Load spaCy model for local NLP processing
nlp = spacy.load("en_core_web_sm")

# Load Hugging Face summarization model with authentication
summarizer = pipeline(
    "summarization",
    model="facebook/bart-large-cnn",
    token=HF_TOKEN,  # Authenticate using Hugging Face API
    device=0  # Use GPU if available
)

# Function to perform a Google search using SERP API
def google_search(query):
    if not SERP_API_KEY:
        return {"error": "SERP API Key not found. Please set SERPAPI_API_KEY in Google Colab Secrets."}
    
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERP_API_KEY
    }
    response = requests.get(SERP_API_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"SERP API Error: {response.status_code}"}

# Function to summarize text using Hugging Face model (dynamic length handling)
def summarize_text(text):
    input_length = len(text.split())

    # Ensure max_length does not exceed input_length
    max_len = min(50, input_length, int(input_length * 1.5))
    min_len = max(5, int(input_length * 0.5))

    return summarizer(text, max_length=max_len, min_length=min_len, do_sample=False)[0]['summary_text']

# Function to check domain trust based on predefined list
def get_domain_trust(domain):
    trust_scores = {
        "mayoclinic.org": 9, "cdc.gov": 10, "who.int": 10, "nih.gov": 10, "healthline.com": 8,
        "forbes.com": 7, "bbc.com": 8, "reuters.com": 9, "nytimes.com": 8, "guardian.com": 8
    }
    return trust_scores.get(domain, 7 if domain.endswith((".org", ".com")) else 4)

# Function to generate a final star rating out of 5
def generate_final_star_rating(score):
    normalized_score = round((score / 100) * 5)  # Normalize final score to 5-star scale
    return "⭐️" * max(1, min(normalized_score, 5))

# Function to fetch webpage content
def fetch_page_content(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException:
        return None

# Placeholder functions for scoring
def check_content_relevance(content, keywords):
    return 8 if content else 4

def check_fast_check_score(content):
    return 7 if content else 3

def check_bias_score(domain):
    return 6 if domain else 5

def check_citation_score(content):
    return 7 if content else 3

def check_https(url):
    return 5 if url.startswith("https") else 0

# Function to evaluate URL validity
def evaluate_url(url, keywords):
    content = fetch_page_content(url)
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.replace("www.", "")
    
    if not content:
        return {"error": "Failed to fetch content."}

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
    final_star_rating = generate_final_star_rating(final_validity_score)
    
    return {"URL": url, "Raw Scores": scores, "Final Star Rating": final_star_rating}

# Example URL evaluation
test_url = "https://www.mayoclinic.org/healthy-lifestyle/infant-and-toddler-health/expert-answers/air-travel-with-infant/faq-20058539"
keywords = ["newborn", "health", "flight", "risks", "air travel", "infant"]
result = evaluate_url(test_url, keywords)

# Display results
if "error" in result:
    print("Error:", result["error"])
else:
    print("Raw Scores:", result["Raw Scores"])
    print("Final Star Rating:", result["Final Star Rating"])
    df = pd.DataFrame([result["Raw Scores"]])
    df.to_csv("url_validity_results.csv", index=False)

# Search and summarize user query
user_prompt = "Are there any health risks for my newborn if I return home after an international flight?"
search_results = google_search(user_prompt)
if "error" in search_results:
    print(search_results["error"])
else:
    snippet = search_results.get("organic_results", [{}])[0].get("snippet", "No results found.")
    summary = summarize_text(snippet)
    print("Summary:", summary)
