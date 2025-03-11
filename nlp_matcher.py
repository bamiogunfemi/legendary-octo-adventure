import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer
from nltk.metrics.distance import edit_distance
from collections import Counter
import re
import math

class NLPMatcher:
    def __init__(self):
        # Download required NLTK data
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
            nltk.data.find('corpora/wordnet')
        except LookupError:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('wordnet', quiet=True)
            nltk.download('averaged_perceptron_tagger', quiet=True)

        self.stop_words = set(stopwords.words('english'))
        self.lemmatizer = WordNetLemmatizer()
        
    def preprocess_text(self, text):
        """Advanced text preprocessing"""
        if not isinstance(text, str):
            return ""
            
        # Convert to lowercase and remove special characters
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Tokenize and lemmatize
        tokens = word_tokenize(text)
        tokens = [self.lemmatizer.lemmatize(token) for token in tokens if token not in self.stop_words]
        
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

    def get_skill_similarity(self, candidate_skill, required_skill):
        """Compute similarity between two skills"""
        # Preprocess both skills
        skill1_tokens = set(self.preprocess_text(candidate_skill))
        skill2_tokens = set(self.preprocess_text(required_skill))
        
        # Exact match
        if skill1_tokens == skill2_tokens:
            return 1.0
            
        # Compute Jaccard similarity
        intersection = len(skill1_tokens & skill2_tokens)
        union = len(skill1_tokens | skill2_tokens)
        
        if union == 0:
            return 0.0
            
        # Add edit distance for better matching
        avg_edit_distance = sum(min(edit_distance(t1, t2) for t2 in skill2_tokens) 
                              for t1 in skill1_tokens) / len(skill1_tokens)
        
        jaccard = intersection / union
        normalized_edit = 1 - (avg_edit_distance / max(len(candidate_skill), len(required_skill)))
        
        return (jaccard + normalized_edit) / 2

    def match_skills(self, candidate_skills, required_skills):
        """Advanced skill matching using NLP"""
        if not candidate_skills or not required_skills:
            return 0, []
            
        matched_skills = []
        total_score = 0
        
        for req_skill in required_skills:
            # Find best matching candidate skill
            best_match = max(
                [(cand_skill, self.get_skill_similarity(cand_skill, req_skill)) 
                 for cand_skill in candidate_skills],
                key=lambda x: x[1]
            )
            
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
        return avg_score, matched_skills

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
