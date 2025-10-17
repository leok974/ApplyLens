"""
Nightly Loader

Loads daily merged analytics data from JSON files.
"""

from pathlib import Path
from datetime import date
import json


def load_nightly(target_date: date) -> dict:
    """
    Load merged analytics data for a specific date.

    Args:
        target_date: Date to load data for

    Returns:
        Dict containing merged metrics (seo, playwright, performance, etc.)
    """
    data_dir = Path("analytics/data")
    date_str = target_date.isoformat()
    json_path = data_dir / f"{date_str}.json"

    if not json_path.exists():
        return {}

    return json.loads(json_path.read_text())
