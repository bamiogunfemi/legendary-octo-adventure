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

            # Match required skills (70% of total score)
            skills_score, matched_required = self.nlp_matcher.match_skills(
                technical_skills,
                required_skills
            )

            # Match nice-to-have skills (30% of total score)
            nice_to_have_score, matched_nice_to_have = self.nlp_matcher.match_skills(
                technical_skills,
                nice_to_have_skills
            )

            # Find missing required skills
            missing_required = list(set(required_skills) - set(matched_required))

            # Find missing nice-to-have skills
            missing_nice_to_have = list(set(nice_to_have_skills) - set(matched_nice_to_have))

            # Calculate weighted scores
            required_weight = 0.7
            nice_to_have_weight = 0.3

            # Calculate overall score
            if required_skills:
                required_score = (len(matched_required) / len(required_skills)) * 100
            else:
                required_score = 0

            if nice_to_have_skills:
                nice_score = (len(matched_nice_to_have) / len(nice_to_have_skills)) * 100
            else:
                nice_score = 0

            # Final weighted score
            overall_score = (required_score * required_weight + 
                           nice_score * nice_to_have_weight)

            # Compile results
            result = {
                'overall_score': overall_score,
                'technical_skills': technical_skills,
                'matched_required_skills': matched_required,
                'matched_nice_to_have': matched_nice_to_have,
                'missing_critical_skills': missing_required,
                'missing_nice_to_have': missing_nice_to_have,
                'evaluation_notes': f"Required Skills Score: {required_score:.1f}%, Nice-to-have Score: {nice_score:.1f}%"
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