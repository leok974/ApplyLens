import os
from elasticsearch import Elasticsearch

ES_ENABLED = os.getenv("ES_ENABLED", "true").lower() == "true"
ES_URL = os.getenv("ES_URL", "http://es:9200")
INDEX = os.getenv("ELASTICSEARCH_INDEX", "gmail_emails")
ES_RECREATE_ON_START = os.getenv("ES_RECREATE_ON_START", "false").lower() == "true"

# Enhanced synonyms for job-search language + ATS platforms
SYNONYMS = [
    # Job search synonyms
    "recruiter, talent partner, sourcer",
    "offer, offer letter, acceptance",
    "application, applied, apply",
    "interview, onsite, on-site, phone screen, screening, call",
    "job, role, position, opening, opportunity",
    "reject, rejection, declined, not moving forward",
    "salary, compensation, pay, wage, rate",
    # ATS platform synonyms (search-time expansion)
    "lever, lever.co, hire.lever.co",
    "workday, myworkdayjobs, wd5.myworkday, myworkday.com",
    "smartrecruiters, smartrecruiters.com, sr.job",
    "greenhouse, greenhouse.io, mailer.greenhouse.io",
]

SETTINGS_AND_MAPPINGS = {
    "settings": {
        "analysis": {
            "filter": {
                "applylens_synonyms": {
                    "type": "synonym",
                    "lenient": True,
                    "synonyms": SYNONYMS
                },
                "applylens_shingle": {
                    "type": "shingle",
                    "min_shingle_size": 2,
                    "max_shingle_size": 3
                }
            },
            "analyzer": {
                "applylens_text": {
                    "tokenizer": "standard",
                    "filter": ["lowercase", "applylens_synonyms"]
                },
                "applylens_text_shingles": {
                    "tokenizer": "standard",
                    "filter": ["lowercase", "applylens_synonyms", "applylens_shingle"]
                },
                # Search analyzer with ATS synonyms for smart matching
                "ats_search_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "applylens_synonyms"]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "id": {"type": "integer"},
            "gmail_id": {"type": "keyword"},
            "thread_id": {"type": "keyword"},
            "from_addr": {"type": "keyword"},
            "sender": {
                "type": "text",
                "analyzer": "standard",
                "search_analyzer": "ats_search_analyzer",
                "fields": {"keyword": {"type": "keyword"}}
            },
            "recipient": {
                "type": "text",
                "analyzer": "standard",
                "search_analyzer": "ats_search_analyzer",
                "fields": {"keyword": {"type": "keyword"}}
            },
            "to": {  # Alias for recipient
                "type": "text",
                "analyzer": "standard",
                "search_analyzer": "ats_search_analyzer"
            },
            "subject": {
                "type": "text",
                "analyzer": "standard",
                "search_analyzer": "ats_search_analyzer",
                "fields": {
                    "raw": {"type": "keyword", "ignore_above": 256},
                    "shingles": {"type": "text", "analyzer": "applylens_text_shingles"}
                }
            },
            "subject_suggest": {
                "type": "completion",
                "analyzer": "simple",
                "preserve_separators": True,
                "preserve_position_increments": True,
                "max_input_length": 100
            },
            "body_text": {
                "type": "text",
                "analyzer": "standard",
                "search_analyzer": "ats_search_analyzer",
                "fields": {
                    "shingles": {"type": "text", "analyzer": "applylens_text_shingles"}
                }
            },
            "body_sayt": {"type": "search_as_you_type"},
            "label": {"type": "keyword"},
            "labels": {"type": "keyword"},  # Gmail labels array
            "label_heuristics": {"type": "keyword"},  # Derived labels
            "company": {"type": "keyword"},
            "role": {"type": "keyword"},
            "source": {"type": "keyword"},
            "source_confidence": {"type": "float"},
            "received_at": {"type": "date"},
            "message_id": {"type": "keyword"}
        }
    }
}

es = Elasticsearch(ES_URL) if ES_ENABLED else None

def ensure_index():
    """Ensure Elasticsearch index exists with retry logic for startup."""
    if not ES_ENABLED or es is None:
        return
    
    # Retry logic for ES connection during startup
    import time
    from elasticsearch.exceptions import ConnectionError
    
    max_retries = 30
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            exists = es.indices.exists(index=INDEX)
            if exists and ES_RECREATE_ON_START:
                es.indices.delete(index=INDEX, ignore=[404])
                exists = False
            if not exists:
                es.indices.create(index=INDEX, body=SETTINGS_AND_MAPPINGS)
            print(f"✓ Elasticsearch index '{INDEX}' is ready")
            return
        except ConnectionError:
            if attempt < max_retries - 1:
                print(f"⏳ Waiting for Elasticsearch (attempt {attempt + 1}/{max_retries})...")
                time.sleep(retry_delay)
                continue
            else:
                print(f"✗ Failed to connect to Elasticsearch after {max_retries} attempts")
                raise
