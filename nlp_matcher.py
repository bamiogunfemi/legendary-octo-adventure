import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer
from nltk.metrics.distance import edit_distance
from collections import Counter
import re
import math
import streamlit as st

class NLPMatcher:
    def __init__(self):
        # Download required NLTK data
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('wordnet', quiet=True)
            nltk.download('averaged_perceptron_tagger', quiet=True)
            self.stop_words = set(stopwords.words('english'))
            self.lemmatizer = WordNetLemmatizer()

            # Enhanced technical skills patterns
            self.tech_skills_patterns = {
                'programming_languages': r'\b(python|java(?:script)?|typescript|go(?:lang)?|ruby|php|swift|kotlin|scala|rust|c\+\+|c#)\b',
                'web_frameworks': r'\b(django|flask|fastapi|spring(?:boot)?|react(?:\.js)?|angular(?:js)?|vue(?:\.js)?|express(?:\.js)?|node(?:\.js)?|next(?:\.js)?)\b',
                'databases': r'\b(post(?:gres)?(?:sql)?|mysql|mongo(?:db)?|redis|elastic(?:search)?|cassandra|dynamo(?:db)?|oracle)\b',
                'cloud': r'\b(aws|amazon|azure|gcp|google cloud|kubernetes|k8s|docker|terraform|ansible|argo(?:cd)?)\b',
                'testing': r'\b(junit|pytest|selenium|cypress|jest|mocha|chai|testing|test automation)\b',
                'devops': r'\b(ci/cd|jenkins|travis|circle(?:ci)?|git(?:hub)?|gitlab|bitbucket|iac|helm|github actions)\b',
                'infrastructure': r'\b(kubernetes|docker|terraform|ansible|puppet|chef|aws|azure|gcp)\b',
                'data_engineering': r'\b(spark|hadoop|kafka|airflow|databricks|snowflake|etl|data pipeline)\b',
                'api': r'\b(rest(?:ful)?|api|graphql|webhook|http[s]?)\b'
            }

        except Exception as e:
            st.error(f"Error initializing NLP components: {str(e)}")
            self.stop_words = set()
            self.lemmatizer = None

    def extract_technical_skills(self, text):
        """Enhanced technical skills extraction from CV text"""
        if not text:
            return []

        # Check if text starts with "CV Content:" prefix
        if isinstance(text, str) and text.startswith("CV Content:"):
            text = text[len("CV Content:"):].strip()

        text = text.lower()
        found_skills = set()

        # Extract skills using patterns
        for category, pattern in self.tech_skills_patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                skill = match.group(0)
                # Normalize skill names
                skill = self.normalize_skill_name(skill)
                found_skills.add(skill)

        # Additional common tech terms
        common_tech_terms = {
            'rest', 'restful', 'api', 'graphql', 'microservices', 'oauth',
            'jwt', 'saml', 'http', 'https', 'tcp/ip', 'webhooks', 'soa',
            'soap', 'grpc', 'openapi', 'swagger', 'postman', 'curl',
            'iac', 'github actions', 'argocd', 'k8s'
        }

        # Look for terms in context
        words = word_tokenize(text)
        for i, word in enumerate(words):
            if word.lower() in common_tech_terms:
                found_skills.add(word.lower())
            # Check for compound terms
            if i < len(words) - 1:
                compound = f"{word.lower()} {words[i+1].lower()}"
                if compound in common_tech_terms:
                    found_skills.add(compound)

        # Log extracted skills
        st.write("Extracted Technical Skills:", sorted(list(found_skills)))

        return sorted(list(found_skills))

    def normalize_skill_name(self, skill):
        """Normalize skill names to standard format"""
        replacements = {
            'javascript': 'javascript',
            'js': 'javascript',
            'typescript': 'typescript',
            'py': 'python',
            'golang': 'go',
            'nodejs': 'node.js',
            'reactjs': 'react',
            'vuejs': 'vue',
            'postgres': 'postgresql',
            'k8s': 'kubernetes',
            'github actions': 'github actions',
            'restful': 'rest',
            'restful api': 'rest api',
            'webservices': 'web services',
            'argo cd': 'argocd',
            'ci/cd': 'ci/cd'
        }

        skill = skill.lower().strip()
        return replacements.get(skill, skill)

    def get_skill_similarity(self, candidate_skill, required_skill):
        """Compute similarity between two skills with improved matching"""
        # Normalize both skills
        skill1 = self.normalize_skill_name(candidate_skill)
        skill2 = self.normalize_skill_name(required_skill)

        # Exact match after normalization
        if skill1 == skill2:
            return 1.0

        # Handle common variations
        if any(variation in skill1 for variation in ['.js', 'js']) and \
           any(variation in skill2 for variation in ['.js', 'js']):
            base1 = skill1.replace('.js', '').replace('js', '')
            base2 = skill2.replace('.js', '').replace('js', '')
            if base1 == base2:
                return 1.0

        # Compute similarity scores
        tokens1 = set(self.preprocess_text(skill1))
        tokens2 = set(self.preprocess_text(skill2))

        # Jaccard similarity
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)

        if union == 0:
            return 0.0

        jaccard = intersection / union

        # Edit distance similarity
        edit_sim = 1 - (edit_distance(skill1, skill2) / max(len(skill1), len(skill2)))

        # Final similarity score
        return (jaccard * 0.6 + edit_sim * 0.4)

    def match_skills(self, candidate_skills, required_skills):
        """Advanced skill matching using NLP"""
        if not candidate_skills or not required_skills:
            return 0, []

        matched_skills = []
        total_score = 0

        # Log the matching process
        st.write("\nSkill Matching Process:")
        st.write("Required Skills:", required_skills)
        st.write("Candidate Skills:", candidate_skills)

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

    def preprocess_text(self, text):
        """Advanced text preprocessing"""
        if not isinstance(text, str):
            return ""

        # Convert to lowercase and remove special characters
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)

        # Tokenize and lemmatize if initialized properly
        tokens = word_tokenize(text)
        if self.lemmatizer:
            tokens = [self.lemmatizer.lemmatize(token) for token in tokens if token not in self.stop_words]
        else:
            tokens = [token for token in tokens if token not in self.stop_words]

        return tokens

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