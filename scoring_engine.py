import pandas as pd
import streamlit as st
from nlp_matcher import NLPMatcher
from datetime import datetime
from deepseek_evaluator import DeepseekEvaluator

class ScoringEngine:
    def __init__(self):
        self.nlp_matcher = NLPMatcher()
        try:
            self.deepseek_evaluator = DeepseekEvaluator()
            self.use_ai = True
        except ValueError:
            st.warning("Deepseek API key not found. Falling back to basic scoring.")
            self.use_ai = False

    def evaluate_cv(self, cv_data, job_requirements):
        """Main evaluation function with detailed scoring breakdown"""
        try:
            # Get CV text
            cv_text = cv_data.get('cv_text', '')
            if not cv_text:
                return self._create_empty_result("No CV content available")

            # Extract technical skills from CV content
            technical_skills = self.nlp_matcher.extract_technical_skills(cv_text)

            # Calculate Skills Match (0-100 points)
            skills_score, skills_breakdown = self._calculate_skills_match(
                technical_skills,
                job_requirements,
                cv_text
            )

            # Calculate Experience Match (0-100 points)
            experience_score, experience_breakdown = self._calculate_experience_match(
                cv_text,
                cv_data.get('years_experience', 0),
                job_requirements
            )

            # Calculate overall score (average of skills and experience)
            overall_score = (skills_score + experience_score) / 2

            # Get Deepseek AI analysis if available
            ai_analysis = {}
            if self.use_ai:
                try:
                    ai_analysis = self.deepseek_evaluator.analyze_cv(cv_text, job_requirements)
                except Exception as e:
                    st.warning(f"AI analysis failed: {str(e)}")

            # Find matched and missing skills
            required_skills = job_requirements.get('required_skills', [])
            nice_to_have_skills = job_requirements.get('nice_to_have_skills', [])

            _, matched_required = self.nlp_matcher.match_skills(technical_skills, required_skills)
            _, matched_nice_to_have = self.nlp_matcher.match_skills(technical_skills, nice_to_have_skills)

            missing_required = list(set(required_skills) - set(matched_required))
            missing_nice_to_have = list(set(nice_to_have_skills) - set(matched_nice_to_have))

            # Compile evaluation notes
            evaluation_notes = (
                f"Skills Match Score: {skills_score:.1f}/100\n"
                f"- Essential Skills Coverage: {skills_breakdown['essential']}/50\n"
                f"- Skill Proficiency: {skills_breakdown['proficiency']}/30\n"
                f"- Additional Skills: {skills_breakdown['additional']}/20\n\n"
                f"Experience Match Score: {experience_score:.1f}/100\n"
                f"- Years of Experience: {experience_breakdown['years']}/50\n"
                f"- Industry Alignment: {experience_breakdown['industry']}/30\n"
                f"- Role Responsibilities: {experience_breakdown['role']}/20\n\n"
            )

            if ai_analysis:
                evaluation_notes += "\nAI Analysis:\n"
                evaluation_notes += f"Skills Analysis:\n{ai_analysis.get('skills_analysis', '')}\n"
                evaluation_notes += f"Experience Analysis:\n{ai_analysis.get('experience_analysis', '')}\n"
                evaluation_notes += f"Overall Recommendation:\n{ai_analysis.get('overall_recommendation', '')}"

            # Compile results
            result = {
                'overall_score': overall_score,
                'technical_skills': technical_skills,
                'matched_required_skills': matched_required,
                'matched_nice_to_have': matched_nice_to_have,
                'missing_critical_skills': missing_required,
                'missing_nice_to_have': missing_nice_to_have,
                'evaluation_notes': evaluation_notes,
                'skills_score': skills_score,
                'experience_score': experience_score,
                'ai_analysis': ai_analysis
            }

            return result

        except Exception as e:
            return self._create_empty_result(f"Error during evaluation: {str(e)}")

    def _calculate_skills_match(self, technical_skills, job_requirements, cv_text):
        """Calculate detailed skills match score"""
        required_skills = job_requirements.get('required_skills', [])
        if not required_skills:
            return 0, {'essential': 0, 'proficiency': 0, 'additional': 0}

        # Essential Skills Coverage (0-50 points)
        _, matched_required = self.nlp_matcher.match_skills(technical_skills, required_skills)
        coverage_ratio = len(matched_required) / len(required_skills)

        if coverage_ratio == 1:
            essential_score = 50
        elif coverage_ratio >= 0.75:
            essential_score = 40
        elif coverage_ratio >= 0.5:
            essential_score = 25
        else:
            essential_score = min(10, coverage_ratio * 20)

        # Skill Proficiency (0-30 points)
        proficiency_keywords = {
            'expert': ['expert', 'advanced', 'senior', 'lead', 'architect'],
            'intermediate': ['intermediate', 'experienced', 'proficient']
        }

        cv_text_lower = cv_text.lower()
        if any(keyword in cv_text_lower for keyword in proficiency_keywords['expert']):
            proficiency_score = 30
        elif any(keyword in cv_text_lower for keyword in proficiency_keywords['intermediate']):
            proficiency_score = 20
        else:
            proficiency_score = 10

        # Additional Relevant Skills (0-20 points)
        nice_to_have = job_requirements.get('nice_to_have_skills', [])
        _, matched_nice_to_have = self.nlp_matcher.match_skills(technical_skills, nice_to_have)

        extra_skills = len(technical_skills) - len(matched_required)
        if extra_skills >= 5 and matched_nice_to_have:
            additional_score = 20
        elif extra_skills >= 3 or matched_nice_to_have:
            additional_score = 15
        else:
            additional_score = 5

        total_score = essential_score + proficiency_score + additional_score
        breakdown = {
            'essential': essential_score,
            'proficiency': proficiency_score,
            'additional': additional_score
        }

        return total_score, breakdown

    def _calculate_experience_match(self, cv_text, years_experience, job_requirements):
        """Calculate detailed experience match score"""
        required_years = job_requirements.get('required_years', 0)

        # Years of Experience (0-50 points)
        if years_experience >= required_years:
            years_score = 50
        else:
            years_score = max(0, 50 - ((required_years - years_experience) * 5))

        # Industry Alignment (0-30 points)
        industry_keywords = job_requirements.get('role', '').lower().split()
        cv_text_lower = cv_text.lower()

        role_matches = sum(1 for keyword in industry_keywords if keyword in cv_text_lower)
        if role_matches >= len(industry_keywords) * 0.8:
            industry_score = 30
        elif role_matches >= len(industry_keywords) * 0.5:
            industry_score = 20
        else:
            industry_score = 10

        # Role Responsibilities (0-20 points)
        responsibility_score = 20 if years_experience >= required_years else 15

        total_score = years_score + industry_score + responsibility_score
        breakdown = {
            'years': years_score,
            'industry': industry_score,
            'role': responsibility_score
        }

        return total_score, breakdown

    def _create_empty_result(self, error_message):
        """Create an empty result with error message"""
        return {
            'overall_score': 0,
            'technical_skills': [],
            'matched_required_skills': [],
            'matched_nice_to_have': [],
            'missing_critical_skills': [],
            'missing_nice_to_have': [],
            'evaluation_notes': error_message,
            'skills_score': 0,
            'experience_score': 0,
            'ai_analysis': {}
        }