import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
import pandas as pd
import spacy
import os
from google.colab import userdata
from transformers import pipeline

class URLValidator:
    """
    A class to validate URLs based on various trust factors and provide a final validity score.
    """

    def __init__(self):
        """Initialize API keys, NLP model, and summarization pipeline."""
        self.HF_TOKEN = userdata.get("HF_TOKEN") or os.getenv("HF_TOKEN")  # Hugging Face Token
        self.SERP_API_KEY = userdata.get("SERPAPI_API_KEY") or os.getenv("SERPAPI_API_KEY")  # SERP API Key
        self.SERP_API_URL = "https://serpapi.com/search"

        if not self.HF_TOKEN:
            print("⚠️ Warning: Hugging Face Token (HF_TOKEN) not found. Please check Google Colab Secrets!")

        # Load NLP model and summarization pipeline
        self.nlp = spacy.load("en_core_web_sm")
        self.summarizer = pipeline(
            "summarization",
            model="facebook/bart-large-cnn",
            token=self.HF_TOKEN,
            device=0  # Use GPU if available
        )

    def google_search(self, query):
        """Perform a Google search using the SERP API."""
        if not self.SERP_API_KEY:
            return {"error": "SERP API Key not found. Please set SERPAPI_API_KEY in Google Colab Secrets."}

        params = {
            "engine": "google",
            "q": query,
            "api_key": self.SERP_API_KEY
        }
        response = requests.get(self.SERP_API_URL, params=params)
        return response.json() if response.status_code == 200 else {"error": f"SERP API Error: {response.status_code}"}

    def summarize_text(self, text):
        """Summarize a given text using Hugging Face summarization model."""
        try:
            input_length = len(text.split())
            max_len = min(50, input_length, int(input_length * 1.5))
            min_len = max(5, int(input_length * 0.5))

            summary = self.summarizer(text, max_length=max_len, min_length=min_len, do_sample=False)
            return summary[0]['summary_text']
        except Exception as e:
            return f"Summarization error: {str(e)}"

    def get_domain_trust(self, domain):
        """Get domain trust score from a predefined list and scale it to percentage."""
        trust_scores = {
            "mayoclinic.org": 90, "cdc.gov": 100, "who.int": 100, "nih.gov": 100, "healthline.com": 80,
            "forbes.com": 70, "bbc.com": 80, "reuters.com": 90, "nytimes.com": 80, "guardian.com": 80
        }
        return trust_scores.get(domain, 70 if domain.endswith((".org", ".com")) else 40)

    def generate_final_star_rating(self, score):
        """Convert the final validity score to a 1-5 star rating."""
        stars = round((score / 100) * 5)  # Normalize to 5-star scale
        return f"⭐️{'⭐️' * max(1, min(stars, 5))} ({stars} / 5)"

    def fetch_page_content(self, url):
        """Fetch webpage content."""
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException:
            return None

    def check_content_relevance(self, content, keywords):
        """Return content relevance score (scaled to 100%)."""
        return 75 if content else 25

    def check_fast_check_score(self, content):
        """Return fact-checking score (scaled to 100%)."""
        return 70 if content else 30

    def check_bias_score(self, domain):
        """Return bias score (scaled to 100%)."""
        return 60 if domain else 50

    def check_citation_score(self, content):
        """Return citation score (scaled to 100%)."""
        return 70 if content else 30

    def check_https(self, url):
        """Check if the URL uses HTTPS for security."""
        return 50 if url.startswith("https") else 0

    def evaluate_url(self, url, keywords):
        """
        Evaluate the trustworthiness of a URL based on multiple scoring factors.
        """
        content = self.fetch_page_content(url)
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace("www.", "")

        if not content:
            return {"error": "Failed to fetch content."}

        scores = {
            "Domain Trust": self.get_domain_trust(domain),
            "Content Relevance": self.check_content_relevance(content, keywords),
            "Fast-Check Score": self.check_fast_check_score(content),
            "Bias Score": self.check_bias_score(domain),
            "Citation Score": self.check_citation_score(content),
            "Security (HTTPS)": self.check_https(url)
        }

        final_validity_score = sum(scores.values()) / len(scores)  # Average score
        scores["Final Validity Score"] = round(final_validity_score, 2)
        final_star_rating = self.generate_final_star_rating(final_validity_score)

        # Extract snippet and summarize
        search_results = self.google_search(" ".join(keywords))
        snippet = search_results.get("organic_results", [{}])[0].get("snippet", "No summary available.")
        summary = self.summarize_text(snippet)

        return {
            "Raw Scores": scores,
            "Final Validity Score": f"{scores['Final Validity Score']}%",
            "Final Star Rating": final_star_rating,
            "Summary": summary
        }

# Example usage
if __name__ == "__main__":
    validator = URLValidator()
    test_url = "https://www.mayoclinic.org/healthy-lifestyle/infant-and-toddler-health/expert-answers/air-travel-with-infant/faq-20058539"
    keywords = ["newborn", "health", "flight", "risks", "air travel", "infant"]
    result = validator.evaluate_url(test_url, keywords)

    # Display results
    if "error" in result:
        print("Error:", result["error"])
    else:
        print("\nRaw Scores:\n")
        for key, value in result["Raw Scores"].items():
            if key != "Final Validity Score":
                print(f'"{key}": {value}')
        print(f'\nFinal Validity Score: {result["Final Validity Score"]}\n')
        print(f'Final Star Rating: {result["Final Star Rating"]}\n')
        print(f'Summary: {result["Summary"]}\n')

        # Save to CSV
        df = pd.DataFrame([result["Raw Scores"]])
        df.to_csv("url_validity_results.csv", index=False)
