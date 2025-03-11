import pandas as pd
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import re

class ScoringEngine:
    def __init__(self):
        # Download all required NLTK data
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)

        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords', quiet=True)

        self.stop_words = set(stopwords.words('english'))

    def preprocess_text(self, text):
        """Preprocess text for analysis"""
        if not isinstance(text, str):
            return ""
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        # Use word_tokenize directly without punkt_tab
        tokens = word_tokenize(text)
        tokens = [t for t in tokens if t not in self.stop_words]
        return " ".join(tokens)

    def check_core_alignment(self, candidate_role, required_role):
        """Check core role alignment"""
        candidate_role = self.preprocess_text(candidate_role)
        required_role = self.preprocess_text(required_role)

        common_words = set(candidate_role.split()) & set(required_role.split())
        total_words = set(required_role.split())

        if not total_words:
            return 0
        return len(common_words) / len(total_words) * 100

    def score_skills_match(self, candidate_skills, required_skills):
        """Score skills match according to framework"""
        if not candidate_skills or not required_skills:
            return 0

        candidate_skills = set(map(str.lower, [s.strip() for s in candidate_skills if s.strip()]))
        required_skills = set(map(str.lower, [s.strip() for s in required_skills if s.strip()]))

        matches = len(candidate_skills & required_skills)
        total_required = len(required_skills)

        if total_required == 0:
            return 0

        match_percentage = (matches / total_required) * 100

        # Essential Skills Coverage (50 points)
        if match_percentage == 100:
            essential_score = 50
        elif match_percentage >= 75:
            essential_score = 40
        elif match_percentage >= 50:
            essential_score = 25
        else:
            essential_score = 10

        # Simplified scoring for other categories
        skill_proficiency = 20  # Default intermediate level
        additional_skills = 15  # Default some valuable skills

        return essential_score + skill_proficiency + additional_skills

    def score_experience_match(self, years_exp, required_years, role_match):
        """Score experience match"""
        try:
            years_exp = float(years_exp) if years_exp else 0
            required_years = float(required_years) if required_years else 1
        except (ValueError, TypeError):
            years_exp = 0
            required_years = 1

        # Years of Experience (40 points)
        years_score = min(40, (years_exp / required_years) * 40)

        # Industry Alignment (40 points)
        industry_score = 30 if role_match else 20

        # Role Responsibilities (20 points)
        role_score = 15  # Default moderate alignment

        return years_score + industry_score + role_score

    def score_education_match(self, education_level, field_of_study, gpa=None):
        """Score education match"""
        if not education_level or not field_of_study:
            return 0

        # Degree Level (50 points)
        degree_scores = {
            'phd': 50,
            'masters': 45,
            'bachelors': 40,
            'other': 20
        }
        degree_score = degree_scores.get(education_level.lower(), 20)

        # Field of Study (30 points)
        technical_fields = {'computer science', 'software engineering', 'engineering'}
        field_score = 30 if field_of_study.lower() in technical_fields else 15

        # Academic Achievement (20 points)
        gpa_score = 15  # Default good achievement

        return degree_score + field_score + gpa_score

    def score_certifications(self, candidate_certs, required_certs):
        """Score certifications"""
        if not candidate_certs or not required_certs:
            return 40  # Default score when no specific certs required

        candidate_certs = set(map(str.lower, [c.strip() for c in candidate_certs if c.strip()]))
        required_certs = set(map(str.lower, [c.strip() for c in required_certs if c.strip()]))

        matches = len(candidate_certs & required_certs)
        total_required = len(required_certs)

        if total_required == 0:
            return 40

        cert_score = (matches / total_required) * 60  # Required certs (60 points)
        additional_score = 30  # Default moderately relevant additional certs

        return cert_score + additional_score

    def evaluate_cv(self, cv_data, job_requirements):
        """Main evaluation function"""
        try:
            # Initial alignment check
            alignment_score = self.check_core_alignment(
                str(cv_data.get('current_role', '')),
                str(job_requirements.get('role', ''))
            )

            # Calculate individual scores
            skills_score = self.score_skills_match(
                cv_data.get('skills', []),
                job_requirements.get('required_skills', [])
            )

            experience_score = self.score_experience_match(
                cv_data.get('years_experience', 0),
                job_requirements.get('required_years', 1),
                cv_data.get('current_role', '') == job_requirements.get('role', '')
            )

            education_score = self.score_education_match(
                cv_data.get('education_level', ''),
                cv_data.get('field_of_study', '')
            )

            certification_score = self.score_certifications(
                cv_data.get('certifications', []),
                job_requirements.get('required_certifications', [])
            )

            # Apply capping rules
            if alignment_score < 50:
                skills_score = min(skills_score, 50)
                experience_score = min(experience_score, 50)
                education_score = min(education_score, 50)
                certification_score = min(certification_score, 50)

            # Calculate overall score
            overall_score = (skills_score + experience_score + education_score + certification_score) / 4

            return {
                'overall_score': overall_score,
                'skills_score': skills_score,
                'experience_score': experience_score,
                'education_score': education_score,
                'certification_score': certification_score,
                'alignment_score': alignment_score
            }
        except Exception as e:
            print(f"Error in evaluate_cv: {str(e)}")
            return {
                'overall_score': 0,
                'skills_score': 0,
                'experience_score': 0,
                'education_score': 0,
                'certification_score': 0,
                'alignment_score': 0
            }