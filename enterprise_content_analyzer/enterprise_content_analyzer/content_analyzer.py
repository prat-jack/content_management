import os
from openai import OpenAI
from dotenv import load_dotenv

class ContentAnalyzer:
    def __init__(self):
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def analyze_content(self, text: str) -> dict:
        """
        Analyzes the given text using the OpenAI API.
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that analyzes business documents. Provide a summary, sentiment (positive/neutral/negative), and 3 key points."
                    },
                    {
                        "role": "user",
                        "content": f"Analyze the following business document:\n\n{text}"
                    }
                ],
                max_tokens=300
            )
            analysis = response.choices[0].message.content.strip()
            # This is a simple way to parse the analysis. A more robust solution
            # might involve asking the model to return JSON.
            lines = analysis.split('\n')
            summary = lines[0].replace('Summary: ', '')
            sentiment = lines[1].replace('Sentiment: ', '')
            key_points = [p.replace('- ', '') for p in lines[3:]]
            
            return {
                "summary": summary,
                "sentiment": sentiment,
                "key_points": key_points
            }

        except Exception as e:
            return {"error": f"An error occurred: {e}"}
