import os
import json
import requests
from typing import Dict, Any, List, Optional

class DeepseekEvaluator:
    def __init__(self):
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable not found")
        
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def analyze_cv(self, cv_text: str, job_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze CV content against job requirements using Deepseek's AI model
        """
        prompt = self._create_analysis_prompt(cv_text, job_requirements)
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": "You are an expert CV evaluator analyzing candidate qualifications."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2  # Lower temperature for more consistent evaluations
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract and structure the analysis
            analysis = self._parse_analysis_response(result['choices'][0]['message']['content'])
            return analysis
            
        except requests.exceptions.RequestException as e:
            return {
                "error": f"Failed to get Deepseek analysis: {str(e)}",
                "skills_analysis": "",
                "experience_analysis": "",
                "overall_recommendation": ""
            }

    def _create_analysis_prompt(self, cv_text: str, job_requirements: Dict[str, Any]) -> str:
        """
        Create a detailed prompt for CV analysis
        """
        return f"""
Please analyze this CV against the job requirements and provide a detailed evaluation.

Job Requirements:
- Role: {job_requirements.get('role', 'Not specified')}
- Required Years: {job_requirements.get('required_years', 0)}
- Required Skills: {', '.join(job_requirements.get('required_skills', []))}
- Nice to Have Skills: {', '.join(job_requirements.get('nice_to_have_skills', []))}

CV Content:
{cv_text}

Please provide a structured analysis with the following:

1. Skills Analysis:
- Match with required skills
- Proficiency level assessment
- Additional relevant skills

2. Experience Analysis:
- Years of relevant experience
- Industry alignment
- Role responsibility match

3. Overall Recommendation:
- Suitability score (0-100)
- Key strengths
- Areas of concern
- Final recommendation

Format your response in a clear, structured manner using these exact sections.
"""

    def _parse_analysis_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse and structure the AI analysis response
        """
        # Extract sections from the response
        sections = {
            "skills_analysis": "",
            "experience_analysis": "",
            "overall_recommendation": ""
        }
        
        current_section = None
        lines = response_text.split('\n')
        
        for line in lines:
            if "Skills Analysis:" in line:
                current_section = "skills_analysis"
                continue
            elif "Experience Analysis:" in line:
                current_section = "experience_analysis"
                continue
            elif "Overall Recommendation:" in line:
                current_section = "overall_recommendation"
                continue
                
            if current_section and line.strip():
                sections[current_section] += line.strip() + "\n"
        
        return sections
