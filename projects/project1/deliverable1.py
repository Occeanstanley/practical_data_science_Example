import requests
import os
import pandas as pd
from urllib.parse import urlparse
from transformers import pipeline

# ✅ Manually set API keys if environment variables are not found
HF_TOKEN = os.getenv("HF_TOKEN", "your_hugging_face_token")  # Replace with actual token
SERP_API_KEY = os.getenv("SERPAPI_API_KEY", "your_serp_api_key")  # Replace with actual key
SERP_API_URL = "https://serpapi.com/search"

# ✅ Load summarization model (only once for efficiency)
summarizer = pipeline(
    "summarization",
    model="facebook/bart-large-cnn",
    token=HF_TOKEN,
    device=0  # Use GPU if available
)

class URLValidator:
    """
    A class to validate URLs based on various trust factors and provide a final validity score.
    """

    def google_search(self, query):
        """Perform a Google search using the SERP API."""
        if not SERP_API_KEY or SERP_API_KEY == "your_serp_api_key":
            return {"error": "SERP API Key is missing. Please provide a valid API key."}

        params = {"engine": "google", "q": query, "api_key": SERP_API_KEY, "num": 1}
        response = requests.get(SERP_API_URL, params=params, timeout=5)
        return response.json() if response.status_code == 200 else {"error": f"SERP API Error: {response.status_code}"}

    def summarize_text(self, text):
        """Summarize text dynamically adjusting length."""
        input_length = len(text.split())
        if input_length < 10:
            return text

        max_len = min(50, input_length, int(input_length * 1.5))
        min_len = max(10, int(input_length * 0.5), min(25, int(input_length * 0.8)))

        summary = summarizer(text, max_length=max_len, min_length=min_len, do_sample=False)
        return summary[0]['summary_text']

    def get_domain_trust(self, domain):
        """Get domain trust score from a predefined list."""
        trust_scores = {
            "mayoclinic.org": 9, "cdc.gov": 10, "who.int": 10, "nih.gov": 10, "healthline.com": 8,
            "forbes.com": 7, "bbc.com": 8, "reuters.com": 9, "nytimes.com": 8, "guardian.com": 8
        }
        return trust_scores.get(domain, 7 if domain.endswith((".org", ".com")) else 4)

    def check_https(self, url):
        """Check if the URL uses HTTPS for security."""
        return 5 if url.startswith("https") else 0

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
        """Return content relevance score (scaled)."""
        return 8 if content else 4

    def check_fast_check_score(self, content):
        """Return fact-checking score."""
        return 7 if content else 3

    def check_bias_score(self, domain):
        """Return bias score."""
        return 6 if domain else 5

    def check_citation_score(self, content):
        """Return citation score."""
        return 7 if content else 3

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

        total_score = sum(scores.values())
        final_validity_score = (total_score / 55) * 100  # Normalize to 0-100
        scores["Final Validity Score"] = round(final_validity_score, 2)

        return {"URL": url, "Raw Scores": scores}

# Example usage
if __name__ == "__main__":
    validator = URLValidator()
    
    # Example URL evaluation
    test_url = "https://www.mayoclinic.org/healthy-lifestyle/infant-and-toddler-health/expert-answers/air-travel-with-infant/faq-20058539"
    keywords = ["newborn", "health", "flight", "risks", "air travel", "infant"]
    result = validator.evaluate_url(test_url, keywords)

    # Perform search and summarization
    user_prompt = "Are there any health risks for my newborn if I return home after an international flight?"
    search_results = validator.google_search(user_prompt)

    if "error" in search_results:
        summary = "No search results available."
    else:
        snippet = search_results.get("organic_results", [{}])[0].get("snippet", "No results found.")
        summary = validator.summarize_text(snippet)

    # Display results
    print("\nRaw Scores:")
    for key, value in result["Raw Scores"].items():
        print(f'"{key}": {value}')

    print(f"\nFinal Validity Score: {result['Raw Scores']['Final Validity Score']}%")
    print(f"\nSummary: {summary}")

    # Save results to CSV
    df = pd.DataFrame([result["Raw Scores"]])
    df.to_csv("url_validity_results.csv", index=False)
