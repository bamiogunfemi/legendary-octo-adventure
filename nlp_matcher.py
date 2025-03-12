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
                'api': r'\b(rest(?:ful)?|api|graphql|webhook|http[s]?)\b'
            }

        except Exception as e:
            st.error(f"Error initializing NLP components: {str(e)}")
            self.stop_words = set()
            self.lemmatizer = None

    def extract_technical_skills(self, text):
        """Extract technical skills from CV text without categorization"""
        if not text:
            return []

        text = text.lower()
        found_skills = set()

        # Extract all skills using combined patterns
        all_patterns = '|'.join([pattern for pattern in self.tech_skills_patterns.values()])
        matches = re.finditer(all_patterns, text, re.IGNORECASE)
        for match in matches:
            skill = match.group(0)
            skill = self.normalize_skill_name(skill)
            found_skills.add(skill)

        # Additional common tech terms
        common_tech_terms = {
            'rest', 'restful', 'api', 'graphql', 'microservices', 'oauth',
            'jwt', 'saml', 'http', 'https', 'webhooks', 'soa',
            'soap', 'grpc', 'openapi', 'swagger', 'postman',
            'iac', 'github actions', 'argocd', 'kubernetes',
            'docker', 'aws', 'azure', 'gcp', 'testing', 'ci/cd'
        }

        # Extract multi-word terms
        words = word_tokenize(text)
        for i, word in enumerate(words):
            word_lower = word.lower()
            if word_lower in common_tech_terms:
                found_skills.add(word_lower)
            if i < len(words) - 1:
                two_words = f"{word_lower} {words[i+1].lower()}"
                if two_words in common_tech_terms:
                    found_skills.add(two_words)
            if i < len(words) - 2:
                three_words = f"{word_lower} {words[i+1].lower()} {words[i+2].lower()}"
                if three_words in common_tech_terms:
                    found_skills.add(three_words)

        return sorted(list(found_skills))

    def match_skills(self, candidate_skills, required_skills):
        """Match candidate skills against required skills"""
        if not candidate_skills or not required_skills:
            return 0, []

        # Log input skills
        st.write("\nMatching Skills:")
        st.write("Candidate Skills:", ", ".join(candidate_skills))
        st.write("Required Skills:", ", ".join(required_skills))

        matched_skills = []
        total_score = 0

        # Normalize all skills
        normalized_candidate = [self.normalize_skill_name(skill) for skill in candidate_skills]
        normalized_required = [self.normalize_skill_name(skill) for skill in required_skills]

        for req_skill in required_skills:
            normalized_req = self.normalize_skill_name(req_skill)

            # Try exact match first
            if normalized_req in normalized_candidate:
                matched_skills.append(req_skill)
                total_score += 1
                st.write(f"✓ Found exact match for '{req_skill}'")
                continue

            # Try fuzzy matching
            best_match = max(
                [(cand_skill, self.get_skill_similarity(cand_skill, req_skill)) 
                 for cand_skill in candidate_skills],
                key=lambda x: x[1]
            )

            if best_match[1] > 0.5:  # Reduced threshold for fuzzy matching
                matched_skills.append(best_match[0])
                total_score += best_match[1]
                st.write(f"✓ Found similar match: '{best_match[0]}' for '{req_skill}' (similarity: {best_match[1]:.2f})")

        avg_score = (total_score / len(required_skills)) * 100 if required_skills else 0
        st.write(f"\nSkills matching score: {avg_score:.1f}%")
        return avg_score, matched_skills

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
            'argo cd': 'argocd',
            'ci/cd': 'ci/cd',
            'aws cloud': 'aws',
            'amazon web services': 'aws',
            'google cloud platform': 'gcp',
            'automated testing': 'testing',
            'test automation': 'testing',
            'unit testing': 'testing',
            'integration testing': 'testing'
        }

        skill = skill.lower().strip()
        skill = re.sub(r'^(?:experienced in |proficient in |knowledge of |expertise in )', '', skill)
        skill = re.sub(r'(?:development|programming|engineer)$', '', skill)
        skill = skill.strip()

        return replacements.get(skill, skill)

    def get_skill_similarity(self, skill1, skill2):
        """Compute similarity between two skills"""
        if not skill1 or not skill2:
            return 0.0

        # Normalize both skills
        skill1 = self.normalize_skill_name(skill1)
        skill2 = self.normalize_skill_name(skill2)

        # Exact match after normalization
        if skill1 == skill2:
            return 1.0

        # Jaccard similarity for tokens
        tokens1 = set(self.preprocess_text(skill1))
        tokens2 = set(self.preprocess_text(skill2))

        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)

        if union == 0:
            return 0.0

        return intersection / union

    def preprocess_text(self, text):
        """Preprocess text for comparison"""
        if not isinstance(text, str):
            return []

        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)

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