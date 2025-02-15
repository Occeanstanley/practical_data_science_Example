from deliverable2 import *

class URLEvaluator:
    def __init__(self, user_prompt, url_to_check):
        self.user_prompt = user_prompt
        self.url_to_check = url_to_check

    def display_info(self):
        print(f"User Query: {self.user_prompt}")
        print(f"URL to Evaluate: {self.url_to_check}")

# Example usage
user_prompt = "Are there any health risks for my newborn if I return home after an international flight?"
url_to_check = "https://www.mayoclinic.org/healthy-lifestyle/infant-and-toddler-health/expert-answers/air-travel-with-infant/faq-20058539"

url_eval = URLEvaluator(user_prompt, url_to_check)
url_eval.display_info()