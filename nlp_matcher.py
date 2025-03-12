import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.metrics.distance import edit_distance
from nltk.stem import WordNetLemmatizer
from collections import Counter
import re
import math
import streamlit as st

class NLPMatcher:
    def __init__(self):
        # Initialize NLTK data
        try:
            # Download required NLTK data silently
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('wordnet', quiet=True)
            nltk.download('averaged_perceptron_tagger', quiet=True)
            self.stop_words = set(stopwords.words('english'))
            self.lemmatizer = WordNetLemmatizer()

            # Updated technical skills patterns based on the example CV
            self.tech_skills_patterns = {
                'programming_languages': r'\b(python|java(?:script)?|typescript|flutter)\b',
                'web_frameworks': r'\b(django|django rest framework|fastapi|react)\b',
                'cloud_platforms': r'\b(aws|gcp|azure|heroku)\b',
                'databases': r'\b(post(?:gres)?(?:sql)?|mysql|mongo(?:db)?|database functions|triggers|django orm)\b',
                'devops': r'\b(docker|kubernetes|github actions|ci/cd|argocd)\b',
                'apis': r'\b(restful api|rest api|api development|grpc|swagger|webhooks|3rd party api)\b',
                'messaging': r'\b(rabbitmq)\b',
                'architecture': r'\b(microservices|multi-tenancy)\b',
                'data_science': r'\b(scikit[-\s]?learn|pytorch|pandas|numpy|matplotlib|statistics)\b',
                'tools': r'\b(advanced excel|technical writing)\b'
            }

        except Exception as e:
            st.error(f"Error initializing NLP components: {str(e)}")
            # Provide fallback values
            self.stop_words = set()
            self.lemmatizer = None
            self.tech_skills_patterns = {}

    def extract_technical_skills(self, text):
        """Enhanced technical skills extraction from CV text"""
        if not text:
            return []

        # Generate variations of the CV text
        all_variations = [text] + self.generate_cv_variations(text)
        found_skills = set()

        # Process each variation
        for variation in all_variations:
            # Extract skills using patterns
            for category, pattern in self.tech_skills_patterns.items():
                matches = re.finditer(pattern, variation, re.IGNORECASE)
                for match in matches:
                    skill = match.group(0)
                    # Normalize skill names
                    skill = self.normalize_skill_name(skill)
                    found_skills.add(skill.title())

            # Check for specific skills
            variation_lower = variation.lower()
            if 'python' in variation_lower:
                found_skills.add('Python')
            if 'aws' in variation_lower:
                found_skills.add('AWS')
            if 'restful' in variation_lower or 'rest api' in variation_lower:
                found_skills.add('RESTful API')
            if 'webhook' in variation_lower:
                found_skills.add('Webhooks')
            if 'gcp' in variation_lower:
                found_skills.add('GCP')
            if 'azure' in variation_lower:
                found_skills.add('Azure')
            if 'argocd' in variation_lower:
                found_skills.add('ArgoCD')
            if 'kubernetes' in variation_lower:
                found_skills.add('Kubernetes')
            if 'docker' in variation_lower:
                found_skills.add('Docker')
            if 'postgres' in variation_lower:
                found_skills.add('PostgreSQL')
            if 'mongodb' in variation_lower:
                found_skills.add('MongoDB')
            if 'test' in variation_lower:
                found_skills.add('Testing')
            if 'github action' in variation_lower:
                found_skills.add('GitHub Actions')

        # Log the skills found
        st.write("\nExtracted Technical Skills:", sorted(list(found_skills)))

        return sorted(list(found_skills))

    def normalize_skill_name(self, skill):
        """Normalize skill names to standard format"""
        replacements = {
            'restful': 'RESTful API',
            'rest api': 'RESTful API',
            'github action': 'GitHub Actions',
            'postgres': 'PostgreSQL',
            'postgresql': 'PostgreSQL',
            'mongo': 'MongoDB',
            'mongodb': 'MongoDB',
            'scikit-learn': 'ScikitLearn',
            'scikit learn': 'ScikitLearn',
            'pytorch': 'PyTorch',
            'numpy': 'NumPy',
            'pandas': 'Pandas',
            'testing': 'Testing',
            'test': 'Testing',
            'webhook': 'Webhooks'
        }

        skill = skill.lower().strip()
        return replacements.get(skill, skill)

    def match_skills(self, candidate_skills, required_skills):
        """Advanced skill matching using NLP"""
        if not candidate_skills or not required_skills:
            return 0, []

        matched_skills = []
        total_score = 0

        # Log the matching process
        st.write("\nSkill Matching Process:")
        st.write("Candidate Skills:", candidate_skills)
        st.write("Required Skills:", required_skills)

        for req_skill in required_skills:
            # Find best matching candidate skill
            best_match = max(
                [(cand_skill, self.get_skill_similarity(cand_skill, req_skill))
                 for cand_skill in candidate_skills],
                key=lambda x: x[1]
            )

            # Log match details
            st.write(f"\nMatching '{req_skill}':")
            st.write(f"Best match: '{best_match[0]}' (similarity: {best_match[1]:.2f})")

            if best_match[1] > 0.6:  # Threshold for considering a match
                matched_skills.append({
                    'required': req_skill,
                    'matched': best_match[0],
                    'similarity': best_match[1]
                })
                total_score += best_match[1]

        if not required_skills:
            return 0, []

        avg_score = (total_score / len(required_skills)) * 100
        st.write(f"\nFinal matching score: {avg_score:.2f}%")
        return avg_score, matched_skills

    def get_skill_similarity(self, candidate_skill, required_skill):
        """Compute similarity between two skills"""
        # Normalize both skills
        skill1 = self.normalize_skill_name(candidate_skill)
        skill2 = self.normalize_skill_name(required_skill)

        # Exact match after normalization
        if skill1.lower() == skill2.lower():
            return 1.0

        # Use lemmatizer if available
        if self.lemmatizer:
            skill1_tokens = [self.lemmatizer.lemmatize(token) for token in word_tokenize(skill1.lower())]
            skill2_tokens = [self.lemmatizer.lemmatize(token) for token in word_tokenize(skill2.lower())]
        else:
            skill1_tokens = word_tokenize(skill1.lower())
            skill2_tokens = word_tokenize(skill2.lower())

        # Convert to sets for comparison
        tokens1 = set(skill1_tokens)
        tokens2 = set(skill2_tokens)

        # Jaccard similarity
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)

        if union == 0:
            return 0.0

        jaccard = intersection / union

        # Edit distance similarity
        edit_sim = 1 - (edit_distance(skill1.lower(), skill2.lower()) / max(len(skill1), len(skill2)))

        # Final similarity score
        return (jaccard * 0.6 + edit_sim * 0.4)

    def preprocess_text(self, text):
        """Advanced text preprocessing"""
        if not isinstance(text, str):
            return []

        # Convert to lowercase and remove special characters
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)

        # Tokenize
        tokens = word_tokenize(text)

        # Remove stopwords and lemmatize if possible
        if self.lemmatizer:
            tokens = [self.lemmatizer.lemmatize(token) for token in tokens if token not in self.stop_words]
        else:
            tokens = [token for token in tokens if token not in self.stop_words]

        return tokens

    def generate_cv_variations(self, cv_text):
        """Generate variations of CV content while maintaining key information"""
        # Split text into sections
        sections = cv_text.split('\n\n')
        variations = []

        # Create variation patterns
        patterns = [
            # Pattern 1: Skills first, then experience
            lambda s: self._format_skills_first(s),
            # Pattern 2: Experience first, then skills
            lambda s: self._format_experience_first(s),
            # Pattern 3: Combined format
            lambda s: self._format_combined(s)
        ]

        for pattern in patterns:
            try:
                variation = pattern(sections)
                if variation:
                    variations.append(variation)
            except Exception as e:
                st.warning(f"Error generating variation: {str(e)}")

        return variations

    def _format_skills_first(self, sections):
        """Format with skills section first"""
        skills_section = ""
        experience_section = ""
        other_sections = []

        for section in sections:
            lower_section = section.lower()
            if 'skills' in lower_section or 'technologies' in lower_section:
                skills_section = section
            elif 'experience' in lower_section or 'work history' in lower_section:
                experience_section = section
            else:
                other_sections.append(section)

        formatted = f"""Technical Expertise
{skills_section}

Professional Background
{experience_section}

{''.join(other_sections)}"""

        return formatted.strip()

    def _format_experience_first(self, sections):
        """Format with experience section first"""
        skills_section = ""
        experience_section = ""
        other_sections = []

        for section in sections:
            lower_section = section.lower()
            if 'skills' in lower_section or 'technologies' in lower_section:
                skills = re.findall(r'\b[A-Za-z+#]+(?:\.[A-Za-z]+)*\b', section)
                skills_section = "Technical Proficiencies:\n" + ", ".join(skills)
            elif 'experience' in lower_section or 'work history' in lower_section:
                experience_section = section
            else:
                other_sections.append(section)

        formatted = f"""Career History
{experience_section}

Technical Skills & Tools
{skills_section}

{''.join(other_sections)}"""

        return formatted.strip()

    def _format_combined(self, sections):
        """Format with combined skills and experience"""
        skills = []
        experiences = []
        other_content = []

        for section in sections:
            lower_section = section.lower()
            if 'skills' in lower_section or 'technologies' in lower_section:
                skills = re.findall(r'\b[A-Za-z+#]+(?:\.[A-Za-z]+)*\b', section)
            elif 'experience' in lower_section or 'work history' in lower_section:
                experiences.append(section)
            else:
                other_content.append(section)

        formatted = f"""Professional Summary
Software developer with expertise in {', '.join(skills[:3])} and other technologies.

Work Experience & Technical Implementations
{' '.join(experiences)}

Core Competencies
{', '.join(skills)}

{''.join(other_content)}"""

        return formatted.strip()

    def compute_tf_idf(self, text, document_set):
        """Compute TF-IDF scores for terms"""
        # Term frequency in the text
        tf = Counter(text)

        # Inverse document frequency
        idf = {}
        doc_count = len(document_set)

        for term in tf:
            doc_with_term = sum(1 for doc in document_set if term in doc)
            idf[term] = math.log(doc_count / (1 + doc_with_term))

        # Compute TF-IDF
        tf_idf = {term: freq * idf[term] for term, freq in tf.items()}
        return tf_idf

    def match_role(self, candidate_role, required_role):
        """Advanced role matching using context"""
        if not candidate_role or not required_role:
            return 0, "No role information provided"

        # Preprocess roles
        candidate_tokens = set(self.preprocess_text(candidate_role))
        required_tokens = set(self.preprocess_text(required_role))

        # Direct token overlap
        overlap_score = len(candidate_tokens & required_tokens) / len(required_tokens) if required_tokens else 0

        # Context matching
        context_score = self.get_skill_similarity(candidate_role, required_role)

        # Combine scores
        final_score = (overlap_score * 0.6 + context_score * 0.4) * 100

        return final_score, "Role context match: {:.1f}%".format(final_score)