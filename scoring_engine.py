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

            # Get Python specific skills
            python_stack_keywords = [
                'python', 'py', 'fastapi', 'asyncio', 'async/await', 'boto3', 'sqlalchemy', 
                'pydantic', 'pytest', 'poetry', 'alembic', 'grafana', 'opentelemetry', 
                'microservices', 'postgresql', 'aws', 'docker', 'kubernetes', 'django', 'flask',
                'celery', 'pandas', 'numpy', 'scipy', 'scikit-learn', 'tensorflow', 'pytorch',
                'keras', 'matplotlib', 'seaborn', 'requests', 'beautifulsoup', 'scrapy', 'selenium',
                'airflow', 'prefect', 'streamlit', 'dash', 'plotly', 'pyspark', 'dask', 'ray',
                'gunicorn', 'uvicorn', 'starlette', 'typer', 'click', 'pipenv', 'virtualenv',
                'conda', 'jupyter', 'pillow', 'opencv', 'nltk', 'spacy', 'gensim', 'transformers',
                'huggingface', 'langchain', 'redis', 'kafka'
            ]
            python_specific_skills = [skill for skill in technical_skills 
                                    if any(kw in skill.lower() for kw in python_stack_keywords)]
            
            # Required Python skills assessment
            python_required = [skill for skill in required_skills 
                              if any(kw in skill.lower() for kw in python_stack_keywords)]
            matched_python_required = [skill for skill in matched_required 
                                      if any(kw in skill.lower() for kw in python_stack_keywords)]
            missing_python_skills = set(python_required) - set(matched_python_required)
            
            # Calculate Python-specific match percentage
            python_match_percentage = (len(matched_python_required) / len(python_required) * 100 
                                     if python_required else 0)
            
            # Compile detailed evaluation notes
            evaluation_notes = (
                f"Skills Match Score: {skills_score:.1f}/100\n"
                f"- Essential Skills Coverage: {skills_breakdown['essential']}/50\n"
                f"- Skill Proficiency: {skills_breakdown['proficiency']}/30\n"
                f"- Additional Skills: {skills_breakdown['additional']}/20\n\n"
                
                f"Python Stack Assessment:\n"
                f"- Python Skills Found: {', '.join(python_specific_skills) if python_specific_skills else 'None'}\n"
                f"- Required Python Skills Match: {python_match_percentage:.1f}%\n"
                f"- Missing Key Python Skills: {', '.join(missing_python_skills) if missing_python_skills else 'None'}\n\n"
                
                f"Experience Match Score: {experience_score:.1f}/100\n"
                f"- Years of Experience: {experience_breakdown['years']}/50 (Required: 7+ years)\n"
                f"- Python Backend Alignment: {experience_breakdown['industry']}/30\n"
                f"- Technical Role Responsibilities: {experience_breakdown['role']}/20\n\n"
                
                f"Recommendation: {'Strongly Consider' if overall_score >= 85 else 'Consider' if overall_score >= 70 else 'Review Further' if overall_score >= 50 else 'Not Recommended'} for Python Backend Developer position\n\n"
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
        """Calculate detailed skills match score with Python stack prioritization"""
        required_skills = job_requirements.get('required_skills', [])
        if not required_skills:
            return 0, {'essential': 0, 'proficiency': 0, 'additional': 0}

        # Essential Skills Coverage (0-50 points)
        _, matched_required = self.nlp_matcher.match_skills(technical_skills, required_skills)
        
        # Check for Python stack technologies from the JD (weighted higher)
        python_stack_keywords = [
            'python', 'fastapi', 'asyncio', 'async/await', 'boto3', 'sqlalchemy', 
            'pydantic', 'pytest', 'poetry', 'alembic', 'grafana', 'opentelemetry', 
            'microservices', 'postgresql', 'aws', 'docker', 'kubernetes'
        ]
        
        # Count Python stack matches and weight them more heavily
        python_matches = sum(1 for skill in matched_required if any(kw in skill.lower() for kw in python_stack_keywords))
        python_required = sum(1 for skill in required_skills if any(kw in skill.lower() for kw in python_stack_keywords))
        
        # Calculate weighted coverage ratio
        standard_matches = len(matched_required) - python_matches
        standard_required = len(required_skills) - python_required
        
        # Python skills are weighted at 1.5x the value of other skills
        weighted_matches = standard_matches + (python_matches * 1.5)
        weighted_total = standard_required + (python_required * 1.5)
        
        coverage_ratio = weighted_matches / weighted_total if weighted_total > 0 else 0
        
        if coverage_ratio >= 1:  # Allow scores over 1 due to weighting
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
        """Calculate detailed experience match score with Python experience emphasis"""
        required_years = job_requirements.get('required_years', 0)
        
        # For the Python backend role, we want 7+ years experience
        if required_years == 0:
            required_years = 7

        # Years of Experience (0-50 points)
        if years_experience >= required_years:
            years_score = 50
        elif years_experience >= required_years - 2:  # Within 2 years of required
            years_score = 40
        elif years_experience >= required_years - 4:  # Within 4 years of required
            years_score = 25
        else:
            years_score = max(0, 50 - ((required_years - years_experience) * 7))  # Steeper penalty

        # Industry Alignment (0-30 points)
        cv_text_lower = cv_text.lower()
        
        # Python backend specific keywords
        python_backend_keywords = [
            'python', 'backend', 'server', 'microservice', 'api', 'fastapi', 'django', 'flask',
            'aws', 'cloud', 'database', 'sql', 'nosql', 'postgresql', 'asyncio', 'asynchronous',
            'software engineer', 'software developer', 'backend developer', 'backend engineer',
            'data validation', 'orm', 'testing', 'ci/cd', 'devops', 'containerization',
            'pydantic', 'pytest', 'poetry', 'alembic', 'sqlalchemy', 'boto3', 'grafana', 
            'opentelemetry', 'starlette', 'uvicorn', 'gunicorn', 'celery', 'redis', 'kafka',
            'elasticsearch', 'pyramid', 'tornado', 'aiohttp', 'sanic', 'falcon', 'graphql',
            'grpc', 'protobuf', 'websocket', 'docker', 'kubernetes', 'terraform', 'ansible',
            'jenkins', 'github actions', 'gitlab ci', 'circleci', 'prometheus', 'datadog',
            'rabbitmq', 'mongodb', 'cassandra', 'dynamodb', 'sqlite', 'memcached', 'caching',
            'event-driven', 'distributed systems', 'microservices architecture', 'api gateway',
            'service mesh', 'jwt', 'oauth', 'authentication', 'authorization'
        ]
        
        # Count how many Python backend keywords are found in the CV
        backend_matches = sum(1 for keyword in python_backend_keywords if keyword in cv_text_lower)
        
        # Calculate score based on Python backend keyword matches
        if backend_matches >= 15:  # Exceptional Python backend experience
            industry_score = 30
        elif backend_matches >= 10:  # Strong Python backend experience
            industry_score = 25
        elif backend_matches >= 7:  # Good Python backend experience
            industry_score = 20
        elif backend_matches >= 4:  # Some Python backend experience
            industry_score = 15
        else:  # Limited Python backend experience
            industry_score = 10
            
        # General industry keywords from job requirements
        industry_keywords = job_requirements.get('role', '').lower().split()
        role_matches = sum(1 for keyword in industry_keywords if keyword in cv_text_lower)
        
        # Boost industry score if general role matches are high
        if role_matches >= len(industry_keywords) * 0.8:
            industry_score = max(industry_score, 25)
        
        # Role Responsibilities (0-20 points)
        # Check for specific Python backend responsibilities
        responsibility_keywords = [
            'architected', 'designed', 'implemented', 'developed', 'built', 'created',
            'microservices', 'apis', 'backend', 'server', 'database', 'cloud', 'aws',
            'deployed', 'maintained', 'optimized', 'scaled', 'tested'
        ]
        
        resp_matches = sum(1 for keyword in responsibility_keywords if keyword in cv_text_lower)
        
        if resp_matches >= 10 and years_experience >= required_years - 2:
            responsibility_score = 20
        elif resp_matches >= 6:
            responsibility_score = 15
        else:
            responsibility_score = 10

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
