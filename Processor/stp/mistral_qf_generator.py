import requests
import pandas as pd
from typing import List

class MistralQualifyingFactorsGenerator:
    """Mistral 7B API generator for STP qualifying factors"""

    def __init__(self, model_name: str = None, api_url: str = None):
        # Use Mistral 7B and the provided endpoint by default
        self.model_name = "mistral:7b"
        self.api_url = api_url or "http://localhost:11434/api/generate"

    def _get_system_prompt(self) -> str:
        """Get the system prompt for STP qualifying factors analysis"""
        return (
            "You are an expert in Social Tipping Points (STP) analysis. You are given a single descriptive passage. "
            "Your only task is to determine the presence of 5 specific qualifying factors in the passage.\n\n"
            "Your output MUST follow the exact structure below — any deviation is a failure:\n\n"
            "1. Environmental problems with perceived societal consequences: [confidence], [description]\n"
            "2. Shared awareness of the problem: [confidence], [description]\n"
            "3. Shared understanding of causes and effects, up to a certain degree: [confidence], [description]\n"
            "4. Expressed perception for a change regarding habits/lifestyle: [confidence], [description]\n"
            "5. Socio-political demand for explanations, solutions and actions: [confidence], [description]\n\n"
            "Rules:\n"
            "- Use only one of the following confidence labels: Strong, Moderate, Weak, Not evident\n"
            "- Each [description] must be brief and based on what is present in the passage. Do not invent facts.\n"
            "- Do NOT say \"the text says\", \"the content mentions\", etc. Describe the subject matter directly.\n"
            "- If there is no evidence for a factor, write: \"Not evident in the provided text\"\n"
            "- You must always give exactly five numbered items using the required format. Do not explain your answer.\n\n"
            "Example response format:\n"
            "1. Environmental problems with perceived societal consequences: Moderate, Environmental and economic implications of deforestation are described.\n"
            "2. Shared awareness of the problem: Strong, Public and policymaker awareness is clearly established.\n"
            "3. Shared understanding of causes and effects, up to a certain degree: Moderate, A connection between consumer behavior and agricultural sustainability is outlined.\n"
            "4. Expressed perception for a change regarding habits/lifestyle: Moderate, Encourages dietary shifts toward sustainable consumption.\n"
            "5. Socio-political demand for explanations, solutions and actions: Strong, Policy reforms and international negotiations are emphasized.\n\n"
            "REMEMBER: Always output exactly five points, using the format and rules above. No summaries, no commentary, no preambles."
        )

    def _format_prompt(self, description: str) -> str:
        """Format the prompt for Mistral (wrap in [/INST])"""
        system_prompt = self._get_system_prompt()
        prompt = f"<s>[INST] {system_prompt}\n\nAnalyze this text for the 5 STP qualifying factors:\n\n{description} [/INST]"
        return prompt

    def generate_factors(self, description: str) -> str:
        """Generate qualifying factors analysis using Mistral 7B API"""
        prompt = self._format_prompt(description)
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False
        }
        try:
            response = requests.post(self.api_url, json=payload, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            # Expecting the result in data['response'] or similar
            if isinstance(data, dict):
                # Try common keys
                for key in ['response', 'result', 'text', 'choices']:
                    if key in data:
                        if isinstance(data[key], str):
                            return data[key].strip()
                        elif isinstance(data[key], list) and data[key]:
                            # If choices, return first text
                            if isinstance(data[key][0], dict) and 'text' in data[key][0]:
                                return data[key][0]['text'].strip()
                            elif isinstance(data[key][0], str):
                                return data[key][0].strip()
            return str(data)
        except Exception as e:
            return f"Error generating factors: {str(e)}"

    def batch_generate(self, descriptions: List[str], batch_size: int = 1) -> List[str]:
        """Generate factors for multiple descriptions (sequential for API)"""
        results = []
        for i, desc in enumerate(descriptions):
            result = self.generate_factors(desc)
            results.append(result)
        return results

    def process_dataframe(self, df: pd.DataFrame, text_column: str = 'content', 
                         stp_only: bool = True, stp_column: str = 'stp_prediction') -> pd.DataFrame:
        """Process DataFrame and add qualifying factors"""
        df = df.copy()
        if stp_only and stp_column in df.columns:
            stp_mask = df[stp_column] == 'STP'
            process_indices = df[stp_mask].index.tolist()
            process_texts = df[stp_mask][text_column].tolist()
        else:
            process_indices = df.index.tolist()
            process_texts = df[text_column].tolist()
        df['qualifying_factors'] = None
        df['has_factors'] = False
        if process_texts:
            results = self.batch_generate(process_texts)
            for idx, result in zip(process_indices, results):
                df.at[idx, 'qualifying_factors'] = result
                df.at[idx, 'has_factors'] = not result.startswith("Error:")
        return df

    def get_memory_usage(self) -> dict:
        """No-op for API usage"""
        return {'message': 'API mode, no local memory usage'}

print("✅ Mistral 7B Qualifying Factors Generator (API mode) ready!")
