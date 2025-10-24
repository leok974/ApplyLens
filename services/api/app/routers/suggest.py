import logging
from typing import Dict, List

from fastapi import APIRouter, Depends, Query

from ..deps.user import get_current_user_email
from ..es import ES_ENABLED, INDEX, es

router = APIRouter(prefix="/suggest", tags=["suggest"])
logger = logging.getLogger(__name__)


@router.get("/")
def suggest(
    q: str = Query(..., min_length=1),
    limit: int = 8,
    user_email: str = Depends(get_current_user_email),
) -> Dict[str, List[str]]:
    """
    Unified suggest: completion over subject + phrase spell-correct + body prefix.

    CRITICAL: NEVER throws 500 - always returns empty suggestions on error
    to prevent blocking search results UI.
    """
    # Quick guards
    if not ES_ENABLED or es is None:
        return {"suggestions": [], "did_you_mean": [], "body_prefix": []}

    if len(q.strip()) < 2:
        return {"suggestions": [], "did_you_mean": [], "body_prefix": []}

    try:
        # Add owner filter to all suggestions
        owner_filter = {"term": {"owner_email.keyword": user_email}}

        body = {
            "suggest": {
                "subject_completion": {
                    "prefix": q,
                    "completion": {
                        "field": "subject_suggest",
                        "skip_duplicates": True,
                        "size": limit,
                        "fuzzy": {"fuzziness": 1},
                    },
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
                            {
                                "field": "subject_shingles",
                                "suggest_mode": "popular",
                                "min_word_length": 2,
                            }
                        ],
                    },
                },
            },
            "size": 5,
            "query": {
                "bool": {
                    "must": {
                        "multi_match": {
                            "query": q,
                            "type": "bool_prefix",
                            "fields": [
                                "body_sayt",
                                "body_sayt._2gram",
                                "body_sayt._3gram",
                            ],
                        }
                    },
                    "filter": [owner_filter],
                }
            },
        }

        res = es.search(index=INDEX, body=body)

        # completion
        completion_opts = (
            res.get("suggest", {}).get("subject_completion", [{}])[0].get("options", [])
        )
        suggestions = [o.get("text") for o in completion_opts]

        # phrase did-you-mean
        phrase_opts = (
            res.get("suggest", {}).get("subject_phrase", [{}])[0].get("options", [])
        )
        did_you_mean = [o.get("text") for o in phrase_opts]

        # body prefix top texts (use subject as a readable suggestion)
        body_prefix = []
        for h in res.get("hits", {}).get("hits", [])[:limit]:
            src = h.get("_source", {})
            if src.get("subject"):
                body_prefix.append(src["subject"])

        return {
            "suggestions": suggestions,
            "did_you_mean": did_you_mean,
            "body_prefix": body_prefix,
        }

    except Exception as e:
        # NEVER 500 — return empty suggestions so UI can still show results
        logger.warning(f"[suggest] error for q='{q}': {e}")
        return {"suggestions": [], "did_you_mean": [], "body_prefix": []}
