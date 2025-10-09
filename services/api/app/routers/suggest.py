from fastapi import APIRouter, Query
from ..es import es, ES_ENABLED, INDEX

router = APIRouter(prefix="/suggest", tags=["suggest"]) 

@router.get("/")
def suggest(q: str = Query(..., min_length=1), limit: int = 8):
    """Unified suggest: completion over subject + phrase spell-correct + body prefix."""
    if not ES_ENABLED or es is None:
        return {"suggestions": [], "did_you_mean": [], "body_prefix": []}

    body = {
        "suggest": {
            "subject_completion": {
                "prefix": q,
                "completion": {
                    "field": "subject_suggest",
                    "skip_duplicates": True,
                    "size": limit,
                    "fuzzy": {"fuzziness": 1}
                }
            },
            "subject_phrase": {
                "text": q,
                "phrase": {
                    "field": "subject_shingles",
                    "size": limit,
                    "real_word_error_likelihood": 0.9,
                    "max_errors": 1,
                    "gram_size": 2,
                    "direct_generator": [
                        {"field": "subject_shingles", "suggest_mode": "popular", "min_word_length": 2}
                    ]
                }
            }
        },
        "size": 5,
        "query": {
            "multi_match": {
                "query": q,
                "type": "bool_prefix",
                "fields": ["body_sayt", "body_sayt._2gram", "body_sayt._3gram"]
            }
        }
    }

    res = es.search(index=INDEX, body=body)

    # completion
    completion_opts = res.get("suggest", {}).get("subject_completion", [{}])[0].get("options", [])
    suggestions = [o.get("text") for o in completion_opts]

    # phrase did-you-mean
    phrase_opts = res.get("suggest", {}).get("subject_phrase", [{}])[0].get("options", [])
    did_you_mean = [o.get("text") for o in phrase_opts]

    # body prefix top texts (use subject as a readable suggestion)
    body_prefix = []
    for h in res.get("hits", {}).get("hits", [])[:limit]:
        src = h.get("_source", {})
        if src.get("subject"):
            body_prefix.append(src["subject"])

    return {"suggestions": suggestions, "did_you_mean": did_you_mean, "body_prefix": body_prefix}
