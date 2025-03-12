import pandas as pd
import streamlit as st
from nlp_matcher import NLPMatcher
from datetime import datetime

class ScoringEngine:
    def __init__(self):
        self.nlp_matcher = NLPMatcher()

    def evaluate_cv(self, cv_data, job_requirements):
        """Main evaluation function with detailed reasoning"""
        try:
            # Get CV text
            cv_text = cv_data.get('cv_text', '')
            if not cv_text:
                return self._create_empty_result("No CV content available")

            # Extract technical skills from CV content
            technical_skills = self.nlp_matcher.extract_technical_skills(cv_text)

            # Get required and nice-to-have skills from job requirements
            required_skills = job_requirements.get('required_skills', [])
            nice_to_have_skills = job_requirements.get('nice_to_have_skills', [])

            # Match required skills
            skills_score, matched_required = self.nlp_matcher.match_skills(
                technical_skills,
                required_skills
            )

            # Match nice-to-have skills
            _, matched_nice_to_have = self.nlp_matcher.match_skills(
                technical_skills,
                nice_to_have_skills
            )

            # Find missing required skills
            missing_required = list(set(required_skills) - set(matched_required))

            # Find missing nice-to-have skills
            missing_nice_to_have = list(set(nice_to_have_skills) - set(matched_nice_to_have))

            # Calculate overall score based on required skills match
            overall_score = skills_score * 0.7  # Weight skills score

            # Compile results
            result = {
                'overall_score': overall_score,
                'technical_skills': technical_skills,
                'matched_required_skills': matched_required,
                'matched_nice_to_have': matched_nice_to_have,
                'missing_critical_skills': missing_required,
                'missing_nice_to_have': missing_nice_to_have,
                'evaluation_notes': ''
            }

            return result

        except Exception as e:
            return self._create_empty_result(f"Error during evaluation: {str(e)}")

    def _create_empty_result(self, error_message):
        """Create an empty result with error message"""
        return {
            'overall_score': 0,
            'technical_skills': [],
            'matched_required_skills': [],
            'matched_nice_to_have': [],
            'missing_critical_skills': [],
            'missing_nice_to_have': [],
            'evaluation_notes': error_message
        }