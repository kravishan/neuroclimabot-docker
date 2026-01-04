import requests
import pandas as pd
from typing import List

class MistralRephraser:
    """Mistral 7B API rephraser for text clarity and structure"""

    def __init__(self, model_name: str = None, api_url: str = None):
        self.model_name = "mistral:7b"
        self.api_url = api_url or "http://localhost:11434/api/generate"

    def _get_rephrasing_prompt(self) -> str:
        """Get the system prompt for text rephrasing"""
        return (
            "You are an expert text editor and academic writer. Your task is to rephrase text passages to make them more accessible and well-structured while maintaining all original meaning and technical accuracy.\n\n"
            "Rephrase or summarize the following text so that it reads as a self-contained and logically structured paragraph about a social tipping point, suitable for display in a conversational UI.\n\n"
            "CRITICAL: You MUST use EXACTLY 80 words or FEWER in your output. This is a strict requirement. Count your words carefully before responding. If the input is too long, summarize it concisely to fit within 80 words. This is a must\n\n"
            "Instructions:\n"
            "- Begin with a brief contextual introduction to the main topic or concept\n"
            "- Clarify the progression of ideas and ensure each part builds logically on the previous one\n"
            "- Where appropriate, group complex points into clearly ordered stages or challenges\n"
            "- Use clear transitions to guide the reader through the argument\n"
            "- Avoid overly technical or dense phrasing, while maintaining a professional and academic tone\n"
            "- Do NOT include any citations, references, or bibliographic information\n"
            "- Do NOT use bullet points, numbered lists, or multiple paragraphs\n"
            "- Do NOT include a title or heading\n"
            "- Do NOT make it several paragraphs; it must be a single paragraph\n"
            "- Output must be exactly ONE complete paragraph that provides the context of the social tipping point\n"
            "- The paragraph MUST end with a complete sentence - never end mid-sentence or with incomplete thoughts\n"
            "- Ensure the paragraph can stand on its own with minimal assumed prior knowledge\n"
            "- If the input text is lengthy, prioritize the most important information and summarize accordingly\n"
            "- FINAL CHECK: Before responding, count your words. If you exceed 80 words, remove less important details until you are at or below 80 words\n\n"
            "This should result in a single, complete paragraph that is accessible, coherent, and well-suited for display in a conversational bot UI.\n\n"
            "Return ONLY the rephrased/summarized text without any additional commentary, explanations, or meta-text."
        )

    def _format_prompt(self, text: str) -> str:
        """Format the prompt for Mistral (wrap in [/INST])"""
        system_prompt = self._get_rephrasing_prompt()
        prompt = f"<s>[INST] {system_prompt}\n\nRephrase/summarize this text:\n\n{text} [/INST]"
        return prompt

    def rephrase_text(self, text: str) -> str:
        """Rephrase or summarize the given text using Mistral 7B API"""
        if not text or len(text.strip()) < 10:
            return text
        
        prompt = self._format_prompt(text)
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9
            }
        }
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=90.0)
            response.raise_for_status()
            data = response.json()
            
            # Extract the response text
            rephrased = None
            if isinstance(data, dict):
                for key in ['response', 'result', 'text', 'choices']:
                    if key in data:
                        if isinstance(data[key], str):
                            rephrased = data[key].strip()
                            break
                        elif isinstance(data[key], list) and data[key]:
                            if isinstance(data[key][0], dict) and 'text' in data[key][0]:
                                rephrased = data[key][0]['text'].strip()
                                break
                            elif isinstance(data[key][0], str):
                                rephrased = data[key][0].strip()
                                break
            
            if not rephrased:
                rephrased = str(data).strip()
            
            # Clean up any remaining artifacts
            rephrased = self._clean_output(rephrased)
            
            return rephrased
            
        except Exception as e:
            print(f"⚠️ Rephrasing failed: {str(e)}")
            return text  # Return original text if rephrasing fails

    def _clean_output(self, text: str) -> str:
        """Clean the output text of common artifacts"""
        # Remove common prefixes/artifacts that models sometimes add
        prefixes_to_remove = [
            "Here is the rephrased text:",
            "Rephrased text:",
            "Here's the rephrased version:",
            "Summary:",
            "Here is a summary:",
            "Here is the text:",
        ]
        
        cleaned = text.strip()
        for prefix in prefixes_to_remove:
            if cleaned.lower().startswith(prefix.lower()):
                cleaned = cleaned[len(prefix):].strip()
        
        # Remove quotes if the entire text is wrapped in them
        if cleaned.startswith('"') and cleaned.endswith('"'):
            cleaned = cleaned[1:-1].strip()
        if cleaned.startswith("'") and cleaned.endswith("'"):
            cleaned = cleaned[1:-1].strip()
        
        return cleaned

    def batch_rephrase(self, texts: List[str], batch_size: int = 1) -> List[str]:
        """Rephrase multiple texts (sequential for API)"""
        results = []
        for i, text in enumerate(texts):
            print(f"Processing {i+1}/{len(texts)}...")
            result = self.rephrase_text(text)
            results.append(result)
        return results

    def process_dataframe(self, df: pd.DataFrame, text_column: str = 'content', 
                         stp_only: bool = True, stp_column: str = 'stp_prediction') -> pd.DataFrame:
        """Process DataFrame and add rephrased text column"""
        df = df.copy()
        
        # Determine which rows to process
        if stp_only and stp_column in df.columns:
            stp_mask = df[stp_column] == 'STP'
            process_indices = df[stp_mask].index.tolist()
            process_texts = df[stp_mask][text_column].tolist()
        else:
            process_indices = df.index.tolist()
            process_texts = df[text_column].tolist()
        
        # Initialize rephrased_content column with original text
        df['rephrased_content'] = df[text_column]
        
        # Process and update
        if process_texts:
            print(f"Rephrasing {len(process_texts)} text chunks...")
            results = self.batch_rephrase(process_texts)
            for idx, result in zip(process_indices, results):
                df.at[idx, 'rephrased_content'] = result
            print("✅ Rephrasing complete!")
        
        return df

    def get_memory_usage(self) -> dict:
        """No-op for API usage"""
        return {'message': 'API mode, no local memory usage'}

print("✅ Mistral 7B Rephraser (API mode) ready!")