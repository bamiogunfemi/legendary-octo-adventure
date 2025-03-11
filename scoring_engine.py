import pandas as pd
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import re

class ScoringEngine:
    def __init__(self):
        # Download required NLTK data
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
        tokens = word_tokenize(text)
        tokens = [t for t in tokens if t not in self.stop_words]
        return " ".join(tokens)

    def check_core_alignment(self, candidate_role, required_role):
        """Check core role alignment"""
        try:
            candidate_role = self.preprocess_text(str(candidate_role))
            required_role = self.preprocess_text(str(required_role))

            if not required_role:
                return 100  # If no required role specified, assume full alignment

            common_words = set(candidate_role.split()) & set(required_role.split())
            total_words = set(required_role.split())

            if not total_words:
                return 100
            return len(common_words) / len(total_words) * 100
        except Exception as e:
            print(f"Error in core alignment check: {str(e)}")
            return 0

    def score_skills_match(self, candidate_skills, required_skills):
        """Score skills match according to framework"""
        try:
            if not candidate_skills or not required_skills:
                return 0, "No skills provided"

            candidate_skills = set(map(str.lower, [s.strip() for s in candidate_skills if s.strip()]))
            required_skills = set(map(str.lower, [s.strip() for s in required_skills if s.strip()]))

            if not required_skills:
                return 50, "No required skills specified"

            matches = len(candidate_skills & required_skills)
            total_required = len(required_skills)
            match_percentage = (matches / total_required) * 100

            # Essential Skills Coverage (50 points)
            if match_percentage == 100:
                return 100, "All required skills present"
            elif match_percentage >= 75:
                return 75, f"Has {matches}/{total_required} required skills"
            elif match_percentage >= 50:
                return 50, f"Has {matches}/{total_required} required skills"
            else:
                return 25, f"Missing most required skills ({matches}/{total_required})"

        except Exception as e:
            print(f"Error in skills match: {str(e)}")
            return 0, "Error evaluating skills"

    def score_experience_match(self, years_exp, required_years):
        """Score experience match"""
        try:
            years_exp = float(str(years_exp).replace('+', '')) if years_exp else 0
            required_years = float(str(required_years).replace('+', '')) if required_years else 1
        except (ValueError, TypeError):
            return 0, "Invalid years format"

        if years_exp >= required_years:
            return 100, f"Meets required {required_years} years of experience"
        elif years_exp >= required_years * 0.75:
            return 75, f"Close to required experience ({years_exp}/{required_years} years)"
        elif years_exp >= required_years * 0.5:
            return 50, f"Partial experience ({years_exp}/{required_years} years)"
        else:
            return 25, f"Insufficient experience ({years_exp}/{required_years} years)"

    def evaluate_cv(self, cv_data, job_requirements):
        """Main evaluation function with detailed reasoning"""
        try:
            reasons = []

            # Check core role alignment
            alignment_score = self.check_core_alignment(
                cv_data.get('current_role', ''),
                job_requirements.get('role', '')
            )

            # Skills evaluation
            skills_score, skills_reason = self.score_skills_match(
                cv_data.get('skills', []),
                job_requirements.get('required_skills', [])
            )
            if skills_score < 50:
                reasons.append(f"Skills: {skills_reason}")

            # Experience evaluation
            exp_score, exp_reason = self.score_experience_match(
                cv_data.get('years_experience', 0),
                job_requirements.get('required_years', 1)
            )
            if exp_score < 50:
                reasons.append(f"Experience: {exp_reason}")

            # Apply alignment cap if needed
            if alignment_score < 50:
                reasons.append(f"Role Alignment: Current role ({cv_data.get('current_role', 'Not specified')}) differs significantly from required role ({job_requirements.get('role', 'Not specified')})")
                skills_score = min(skills_score, 50)
                exp_score = min(exp_score, 50)

            # Calculate overall score
            overall_score = (skills_score + exp_score) / 2

            result = {
                'overall_score': overall_score,
                'skills_score': skills_score,
                'experience_score': exp_score,
                'alignment_score': alignment_score,
                'reasons': reasons if reasons else []
            }

            return result

        except Exception as e:
            print(f"Error in evaluate_cv: {str(e)}")
            return {
                'overall_score': 0,
                'skills_score': 0,
                'experience_score': 0,
                'alignment_score': 0,
                'reasons': ['Error during evaluation: ' + str(e)]
            }