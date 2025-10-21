#!/usr/bin/env python3
"""
Weight Tuning Analysis for Email Risk Detection v3.1

Analyzes user feedback to identify false positives/negatives and recommend
weight adjustments for the 16 heuristics in the v3.1 pipeline.

Usage:
  python scripts/analyze_weights.py --days 30 --output docs/WEIGHT_TUNING_ANALYSIS.md

Environment Variables:
  ES_URL - Elasticsearch endpoint (default: http://localhost:9200)
  ES_INDEX - Email index pattern (default: gmail_emails-*)
"""

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Dict, List

import requests

# Environment configuration
ES_URL = os.environ.get("ES_URL", "http://localhost:9200")
ES_INDEX = os.environ.get("ES_INDEX", "gmail_emails-*")

# Current weights from emails_v3.json pipeline
CURRENT_WEIGHTS = {
    # v3.0 signals
    "domain_mismatch": 25,
    "non_canonical_domain": 25,
    "risky_phrases": 30,  # for 3+ hits
    "pii_request": 20,
    "vague_role": 10,
    "no_calendar_invite": 5,
    "no_career_link": 10,
    # v3.1 signals
    "spf_fail": 10,
    "dkim_fail": 10,
    "dmarc_fail": 15,
    "reply_to_mismatch": 15,
    "link_shorteners": 8,
    "anchor_mismatch": 12,
    "off_brand_urls": 10,
    "risky_attachment": 20,
    "young_domain": 15,
}

# Signal to explanation keyword mapping
SIGNAL_KEYWORDS = {
    "domain_mismatch": "From domain and subject domain differ",
    "non_canonical_domain": "Non-canonical domain",
    "risky_phrases": "Risky recruiting phrases",
    "pii_request": "PII request",
    "vague_role": "Vague role",
    "no_calendar_invite": "No calendar invite",
    "no_career_link": "No career link",
    "spf_fail": "SPF fail",
    "dkim_fail": "DKIM fail",
    "dmarc_fail": "DMARC fail",
    "reply_to_mismatch": "Reply-To domain differs",
    "link_shorteners": "Link shorteners",
    "anchor_mismatch": "Anchor text and href domain differ",
    "off_brand_urls": "Off-brand",
    "risky_attachment": "risky attachment",
    "young_domain": "Domain age < 30 days",
}


def query_emails(days: int = 30) -> Dict[str, any]:
    """Query ES for emails from last N days with user feedback."""
    body = {
        "size": 10000,  # Increase if needed
        "query": {
            "bool": {
                "must": [
                    {"range": {"received_at": {"gte": f"now-{days}d"}}},
                    {"exists": {"field": "user_feedback_verdict"}},
                ]
            }
        },
        "_source": [
            "suspicion_score",
            "suspicious",
            "explanations",
            "user_feedback_verdict",
            "user_feedback_note",
            "from",
            "subject",
        ],
    }

    response = requests.post(
        f"{ES_URL}/{ES_INDEX}/_search",
        json=body,
        headers={"Content-Type": "application/json"},
    )

    if response.status_code != 200:
        raise Exception(f"ES query failed: {response.text}")

    data = response.json()
    total = data["hits"]["total"]["value"]
    emails = [hit["_source"] for hit in data["hits"]["hits"]]

    return {"total": total, "emails": emails}


def categorize_emails(emails: List[Dict]) -> Dict[str, List[Dict]]:
    """Categorize emails by verdict and detection status."""
    categories = {
        "true_positive": [],  # suspicious=true, verdict=scam
        "true_negative": [],  # suspicious=false, verdict=legit
        "false_positive": [],  # suspicious=true, verdict=legit
        "false_negative": [],  # suspicious=false, verdict=scam
        "unsure": [],  # verdict=unsure
    }

    for email in emails:
        suspicious = email.get("suspicious", False)
        verdict = email.get("user_feedback_verdict", "").lower()

        if verdict == "scam":
            if suspicious:
                categories["true_positive"].append(email)
            else:
                categories["false_negative"].append(email)
        elif verdict == "legit":
            if suspicious:
                categories["false_positive"].append(email)
            else:
                categories["true_negative"].append(email)
        elif verdict == "unsure":
            categories["unsure"].append(email)

    return categories


def analyze_signal_performance(categories: Dict[str, List[Dict]]) -> Dict[str, Dict]:
    """Analyze which signals appear most in FP/FN/TP/TN."""
    signal_stats = defaultdict(lambda: {"tp": 0, "tn": 0, "fp": 0, "fn": 0, "total": 0})

    for category, emails in categories.items():
        if category == "unsure":
            continue

        for email in emails:
            explanations = email.get("explanations", [])
            if isinstance(explanations, str):
                explanations = [explanations]

            # Map explanations to signals
            signals_in_email = set()
            for signal_name, keyword in SIGNAL_KEYWORDS.items():
                for exp in explanations:
                    if keyword.lower() in exp.lower():
                        signals_in_email.add(signal_name)
                        break

            # Update stats for each signal
            for signal_name in signals_in_email:
                signal_stats[signal_name]["total"] += 1
                if category == "true_positive":
                    signal_stats[signal_name]["tp"] += 1
                elif category == "true_negative":
                    signal_stats[signal_name]["tn"] += 1
                elif category == "false_positive":
                    signal_stats[signal_name]["fp"] += 1
                elif category == "false_negative":
                    signal_stats[signal_name]["fn"] += 1

    return dict(signal_stats)


def calculate_precision_recall(stats: Dict) -> Dict[str, float]:
    """Calculate precision and recall for a signal."""
    tp = stats["tp"]
    fp = stats["fp"]
    fn = stats["fn"]

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        (2 * precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return {"precision": precision, "recall": recall, "f1": f1}


def recommend_weight_adjustments(signal_stats: Dict[str, Dict]) -> Dict[str, Dict]:
    """Recommend weight adjustments based on signal performance."""
    recommendations = {}

    for signal_name, stats in signal_stats.items():
        if stats["total"] == 0:
            continue

        current_weight = CURRENT_WEIGHTS.get(signal_name, 0)
        metrics = calculate_precision_recall(stats)

        # Recommendation logic:
        # - High precision (>0.9), low recall: Increase weight to catch more
        # - Low precision (<0.7): Decrease weight to reduce false positives
        # - Balanced (0.7-0.9): Keep current weight

        precision = metrics["precision"]
        recall = metrics["recall"]
        f1 = metrics["f1"]

        if precision >= 0.9 and recall < 0.7:
            # Excellent precision, poor recall → increase weight
            adjustment = "+5"
            new_weight = current_weight + 5
            reason = f"High precision ({precision:.2f}), low recall ({recall:.2f})"
        elif precision < 0.7:
            # Poor precision → decrease weight
            adjustment = "-5"
            new_weight = max(5, current_weight - 5)  # Minimum weight 5
            reason = f"Low precision ({precision:.2f}), too many false positives"
        elif f1 >= 0.85:
            # Excellent F1 → consider increasing weight
            adjustment = "+3"
            new_weight = current_weight + 3
            reason = f"Excellent F1 score ({f1:.2f}), strong signal"
        else:
            # Balanced → keep current weight
            adjustment = "0"
            new_weight = current_weight
            reason = "Balanced performance, no change needed"

        recommendations[signal_name] = {
            "current_weight": current_weight,
            "adjustment": adjustment,
            "new_weight": new_weight,
            "reason": reason,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": stats["tp"],
            "fp": stats["fp"],
            "fn": stats["fn"],
            "total": stats["total"],
        }

    return recommendations


def generate_markdown_report(
    categories: Dict[str, List[Dict]],
    signal_stats: Dict[str, Dict],
    recommendations: Dict[str, Dict],
    days: int,
) -> str:
    """Generate markdown report with analysis and recommendations."""
    total_emails = sum(len(emails) for emails in categories.values())
    tp_count = len(categories["true_positive"])
    tn_count = len(categories["true_negative"])
    fp_count = len(categories["false_positive"])
    fn_count = len(categories["false_negative"])
    unsure_count = len(categories["unsure"])

    # Calculate overall accuracy
    accuracy = (
        (tp_count + tn_count) / (tp_count + tn_count + fp_count + fn_count)
        if (tp_count + tn_count + fp_count + fn_count) > 0
        else 0.0
    )
    fp_rate = fp_count / (fp_count + tn_count) if (fp_count + tn_count) > 0 else 0.0
    fn_rate = fn_count / (fn_count + tp_count) if (fn_count + tp_count) > 0 else 0.0

    report = f"""# Weight Tuning Analysis — Email Risk v3.1

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Analysis Period**: Last {days} days
**Total Emails with Feedback**: {total_emails}

---

## Executive Summary

### Overall Performance

| Metric | Count | Percentage |
|--------|-------|------------|
| **True Positives** (Scam correctly detected) | {tp_count} | {(tp_count/total_emails*100):.1f}% |
| **True Negatives** (Legit correctly cleared) | {tn_count} | {(tn_count/total_emails*100):.1f}% |
| **False Positives** (Legit marked as scam) | {fp_count} | {(fp_count/total_emails*100):.1f}% |
| **False Negatives** (Scam missed) | {fn_count} | {(fn_count/total_emails*100):.1f}% |
| **Unsure** (User uncertain) | {unsure_count} | {(unsure_count/total_emails*100):.1f}% |

### Key Metrics

- **Accuracy**: {accuracy:.1%} (correct classifications / total)
- **False Positive Rate**: {fp_rate:.1%} (legit emails wrongly flagged)
- **False Negative Rate**: {fn_rate:.1%} (scams missed)

### Recommendations Summary

"""

    # Count recommendations by type
    increase_count = sum(
        1 for r in recommendations.values() if r["adjustment"].startswith("+")
    )
    decrease_count = sum(
        1 for r in recommendations.values() if r["adjustment"].startswith("-")
    )
    no_change_count = sum(1 for r in recommendations.values() if r["adjustment"] == "0")

    report += f"""- **Increase weight**: {increase_count} signals (high precision, need better coverage)
- **Decrease weight**: {decrease_count} signals (low precision, too many false positives)
- **No change**: {no_change_count} signals (balanced performance)

---

## Signal Performance Analysis

### Performance Matrix

| Signal | Current Weight | TP | FP | FN | Precision | Recall | F1 Score | Recommendation |
|--------|----------------|----|----|-----|-----------|--------|----------|----------------|
"""

    # Sort by F1 score (best to worst)
    sorted_signals = sorted(
        recommendations.items(), key=lambda x: x[1]["f1"], reverse=True
    )

    for signal_name, rec in sorted_signals:
        report += f"| {signal_name.replace('_', ' ').title()} | {rec['current_weight']} | {rec['tp']} | {rec['fp']} | {rec['fn']} | {rec['precision']:.2f} | {rec['recall']:.2f} | {rec['f1']:.2f} | {rec['adjustment']} pts |\\n"

    report += """

### Top Performing Signals (F1 > 0.80)

"""

    top_performers = [(name, rec) for name, rec in sorted_signals if rec["f1"] > 0.80]

    if top_performers:
        for signal_name, rec in top_performers:
            report += f"""**{signal_name.replace('_', ' ').title()}**
- Current weight: {rec['current_weight']} pts
- F1 Score: {rec['f1']:.2f} (Precision: {rec['precision']:.2f}, Recall: {rec['recall']:.2f})
- Occurrences: {rec['tp']} TP, {rec['fp']} FP, {rec['fn']} FN
- ✅ **Strong signal** — {rec['reason']}

"""
    else:
        report += "_No signals with F1 > 0.80 in current dataset._\\n\\n"

    report += """### Underperforming Signals (Precision < 0.70)

"""

    underperformers = [
        (name, rec) for name, rec in sorted_signals if rec["precision"] < 0.70
    ]

    if underperformers:
        for signal_name, rec in underperformers:
            report += f"""**{signal_name.replace('_', ' ').title()}**
- Current weight: {rec['current_weight']} pts
- Precision: {rec['precision']:.2f} (Recall: {rec['recall']:.2f})
- Occurrences: {rec['tp']} TP, {rec['fp']} FP ({rec['fp']/(rec['fp']+rec['tp'])*100:.1f}% false positive rate)
- ⚠️ **Needs tuning** — {rec['reason']}

"""
    else:
        report += "_No signals with precision < 0.70 in current dataset._\\n\\n"

    report += """---

## Recommended Weight Adjustments

### Changes to Apply

Apply these changes to `infra/elasticsearch/pipelines/emails_v3.json`:

```json
{
"""

    # Show only signals that need adjustments
    changes = {
        name: rec for name, rec in recommendations.items() if rec["adjustment"] != "0"
    }

    if changes:
        for i, (signal_name, rec) in enumerate(changes.items()):
            comma = "," if i < len(changes) - 1 else ""
            report += f"""  "{signal_name}": {rec['new_weight']}  // was {rec['current_weight']} ({rec['adjustment']} pts){comma}
"""
        report += """}
```

**Rationale**:

"""
        for signal_name, rec in changes.items():
            report += f"- **{signal_name}**: {rec['reason']}\\n"
    else:
        report += """  // No changes recommended based on current data
}
```

**Rationale**: All signals are performing within acceptable ranges (0.70-0.90 precision).

"""

    report += """
### Before/After Comparison

| Signal | Before | After | Change | Expected Impact |
|--------|--------|-------|--------|----------------|
"""

    for signal_name, rec in recommendations.items():
        if rec["adjustment"] != "0":
            impact = (
                "Reduce false positives"
                if rec["adjustment"].startswith("-")
                else "Improve detection coverage"
            )
            report += f"| {signal_name.replace('_', ' ').title()} | {rec['current_weight']} | {rec['new_weight']} | {rec['adjustment']} | {impact} |\\n"

    if not changes:
        report += "| _No changes_ | — | — | — | — |\\n"

    report += """

---

## False Positive Analysis

### Common Patterns in False Positives

"""

    if fp_count > 0:
        # Analyze common signals in false positives
        fp_signal_counts = defaultdict(int)
        for email in categories["false_positive"]:
            explanations = email.get("explanations", [])
            if isinstance(explanations, str):
                explanations = [explanations]
            for signal_name, keyword in SIGNAL_KEYWORDS.items():
                for exp in explanations:
                    if keyword.lower() in exp.lower():
                        fp_signal_counts[signal_name] += 1
                        break

        sorted_fp_signals = sorted(
            fp_signal_counts.items(), key=lambda x: x[1], reverse=True
        )

        report += "**Top Signals in False Positives**:\\n\\n"
        for signal_name, count in sorted_fp_signals[:5]:
            pct = (count / fp_count) * 100
            report += f"- **{signal_name.replace('_', ' ').title()}**: {count}/{fp_count} emails ({pct:.1f}%)\\n"

        report += """

**Sample False Positive**:

"""
        if categories["false_positive"]:
            sample_fp = categories["false_positive"][0]
            report += f"""```
From: {sample_fp.get('from', 'N/A')}
Subject: {sample_fp.get('subject', 'N/A')}
Suspicion Score: {sample_fp.get('suspicion_score', 0)}
Explanations: {', '.join(sample_fp.get('explanations', []) if isinstance(sample_fp.get('explanations', []), list) else [sample_fp.get('explanations', '')])}
User Note: {sample_fp.get('user_feedback_note', 'N/A')}
```

"""
    else:
        report += "_No false positives in current dataset._\\n\\n"

    report += """---

## False Negative Analysis

### Missed Scams

"""

    if fn_count > 0:
        report += f"""**Total Scams Missed**: {fn_count}

**Sample False Negative**:

"""
        sample_fn = categories["false_negative"][0]
        report += f"""```
From: {sample_fn.get('from', 'N/A')}
Subject: {sample_fn.get('subject', 'N/A')}
Suspicion Score: {sample_fn.get('suspicion_score', 0)}
Explanations: {', '.join(sample_fn.get('explanations', []) if isinstance(sample_fn.get('explanations', []), list) else [sample_fn.get('explanations', '')])}
User Note: {sample_fn.get('user_feedback_note', 'N/A')}
```

**Why Missed**:
- Suspicion score below 40 threshold (actual: {sample_fn.get('suspicion_score', 0)})
- Signals present: {len(sample_fn.get('explanations', []))}
- Recommendation: Increase weights of detected signals or add new heuristics

"""
    else:
        report += "_No false negatives in current dataset. Excellent coverage!_\\n\\n"

    report += f"""---

## Next Steps

### Immediate (This Week)

1. **Review Recommendations**: Evaluate proposed weight changes
2. **Update Pipeline**: Apply changes to `infra/elasticsearch/pipelines/emails_v3.json`
3. **Re-test**: Run `python scripts/generate_test_emails.py` to validate
4. **Deploy to Staging**: Test with staging emails before production

### Short-term (This Month)

1. **Collect More Feedback**: Need at least 100 emails per signal for statistical significance
2. **Monitor Impact**: Track accuracy metrics after weight changes
3. **Iterate**: Re-run analysis weekly to measure improvements
4. **Document Learnings**: Update EMAIL_RISK_DETECTION_V3.md with findings

### Long-term (Next Quarter)

1. **ML Integration**: Train supervised model on feedback data
2. **A/B Testing**: Test weight variations with random sample groups
3. **External Enrichment**: Integrate VirusTotal/PhishTank for URL validation
4. **Automated Tuning**: Build feedback loop to auto-adjust weights

---

## Appendix: Raw Data

### Email Distribution by Category

```json
{{
  "true_positive": {tp_count},
  "true_negative": {tn_count},
  "false_positive": {fp_count},
  "false_negative": {fn_count},
  "unsure": {unsure_count}
}}
```

### Signal Statistics

```json
{json.dumps(signal_stats, indent=2)}
```

---

**Status**: 📊 Analysis Complete
**Action Required**: Review recommendations and apply weight changes
**Re-analysis Recommended**: Weekly (or after 100+ new feedback entries)

"""

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Analyze email risk detection weights based on user feedback"
    )
    parser.add_argument(
        "--days", type=int, default=30, help="Number of days to analyze (default: 30)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="docs/WEIGHT_TUNING_ANALYSIS.md",
        help="Output markdown file (default: docs/WEIGHT_TUNING_ANALYSIS.md)",
    )
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")

    args = parser.parse_args()

    print(f"Analyzing emails from last {args.days} days...")

    # Query ES for emails with feedback
    try:
        data = query_emails(args.days)
        print(f"Found {data['total']} emails with user feedback")
    except Exception as e:
        print(f"Error querying Elasticsearch: {e}")
        return 1

    if data["total"] == 0:
        print("⚠️  No emails with user feedback found. Cannot perform analysis.")
        print("💡 Tip: Submit feedback via EmailRiskBanner UI to collect data")
        return 1

    # Categorize emails
    categories = categorize_emails(data["emails"])
    print(f"  ✅ True Positives: {len(categories['true_positive'])}")
    print(f"  ✅ True Negatives: {len(categories['true_negative'])}")
    print(f"  ⚠️  False Positives: {len(categories['false_positive'])}")
    print(f"  ⚠️  False Negatives: {len(categories['false_negative'])}")
    print(f"  ❓ Unsure: {len(categories['unsure'])}")

    # Analyze signal performance
    signal_stats = analyze_signal_performance(categories)
    print(f"\\nAnalyzed {len(signal_stats)} signals")

    # Generate recommendations
    recommendations = recommend_weight_adjustments(signal_stats)
    changes = sum(1 for r in recommendations.values() if r["adjustment"] != "0")
    print(f"Generated {changes} weight adjustment recommendations")

    # Generate markdown report
    report = generate_markdown_report(
        categories, signal_stats, recommendations, args.days
    )

    # Write to file
    with open(args.output, "w") as f:
        f.write(report)

    print(f"\\n✅ Report saved to {args.output}")
    print("\\n📊 Summary:")
    print(
        f"   - Accuracy: {((len(categories['true_positive']) + len(categories['true_negative'])) / data['total'] * 100):.1f}%"
    )
    print(
        f"   - False Positive Rate: {(len(categories['false_positive']) / (len(categories['false_positive']) + len(categories['true_negative'])) * 100 if (len(categories['false_positive']) + len(categories['true_negative'])) > 0 else 0):.1f}%"
    )
    print(f"   - Recommended Changes: {changes} signals")

    return 0


if __name__ == "__main__":
    exit(main())
