"""
Automation API Router

Endpoints for email automation scoring, analysis, and management.
Includes risk score recomputation and summary statistics.
"""

import subprocess
import os
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Email
from app.metrics import (
    risk_recompute_requests,
    risk_recompute_duration,
    risk_emails_scored_total
)

router = APIRouter(prefix="/automation", tags=["automation"])


@router.post("/recompute")
async def recompute_all_risk(
    background_tasks: BackgroundTasks,
    dry_run: bool = False,
    batch_size: int = 500
):
    """
    Trigger risk score recomputation for all emails.
    
    This endpoint runs the analyze_risk.py script which:
    - Computes risk scores using heuristics
    - Updates risk_score and features_json fields
    - Returns processing statistics
    
    Args:
        dry_run: If True, only show what would be updated (no DB changes)
        batch_size: Number of emails to process per batch
    
    Returns:
        Job status and output
    """
    risk_recompute_requests.inc()
    
    try:
        # Build command
        env = os.environ.copy()
        env["DRY_RUN"] = "1" if dry_run else "0"
        env["BATCH_SIZE"] = str(batch_size)
        
        # Run script
        with risk_recompute_duration.time():
            result = subprocess.run(
                ["python", "scripts/analyze_risk.py"],
                capture_output=True,
                text=True,
                env=env,
                timeout=600  # 10 minute timeout
            )
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Risk recomputation failed: {result.stderr}"
            )
        
        # Parse output for statistics
        output_lines = result.stdout.split("\n")
        stats = {}
        for line in output_lines:
            if "Total processed:" in line:
                stats["processed"] = int(line.split(":")[-1].strip())
            elif "Total updated:" in line:
                stats["updated"] = int(line.split(":")[-1].strip())
            elif "Duration:" in line:
                stats["duration_seconds"] = float(line.split(":")[1].split()[0])
        
        # Update metrics
        if stats.get("processed"):
            risk_emails_scored_total.inc(stats["processed"])
        
        return {
            "status": "success",
            "dry_run": dry_run,
            "batch_size": batch_size,
            "statistics": stats,
            "output": result.stdout
        }
        
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail="Risk recomputation timed out after 10 minutes"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error running risk recomputation: {str(e)}"
        )


@router.get("/risk-summary")
async def get_risk_summary(
    category: str = None,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """
    Get risk score summary statistics.
    
    Args:
        category: Filter by email category (bills, promotions, etc.)
        days: Number of days to include (default: 7)
    
    Returns:
        Risk score distribution and statistics
    """
    # Build query
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    filters = [Email.received_at >= cutoff_date]
    if category:
        filters.append(Email.category == category)
    
    # Get statistics
    stmt = select(
        func.count(Email.id).label("total"),
        func.avg(Email.risk_score).label("avg_score"),
        func.min(Email.risk_score).label("min_score"),
        func.max(Email.risk_score).label("max_score"),
        func.percentile_cont(0.5).within_group(Email.risk_score).label("median_score")
    ).where(and_(*filters))
    
    result = db.execute(stmt).first()
    
    # Get distribution by risk level
    risk_levels = [
        ("low", 0, 30),
        ("medium", 30, 70),
        ("high", 70, 100)
    ]
    
    distribution = {}
    for level, min_score, max_score in risk_levels:
        count_stmt = select(func.count(Email.id)).where(
            and_(
                *filters,
                Email.risk_score >= min_score,
                Email.risk_score < max_score
            )
        )
        count = db.execute(count_stmt).scalar()
        distribution[level] = count
    
    # Get top risky emails
    top_risky_stmt = select(
        Email.id,
        Email.sender,
        Email.subject,
        Email.risk_score,
        Email.category,
        Email.received_at
    ).where(
        and_(*filters)
    ).order_by(Email.risk_score.desc()).limit(10)
    
    top_risky = db.execute(top_risky_stmt).all()
    
    return {
        "period": {
            "days": days,
            "from": cutoff_date.isoformat(),
            "to": datetime.now(timezone.utc).isoformat()
        },
        "filter": {
            "category": category
        },
        "statistics": {
            "total_emails": result.total or 0,
            "average_risk_score": round(float(result.avg_score or 0), 2),
            "min_risk_score": round(float(result.min_score or 0), 2),
            "max_risk_score": round(float(result.max_score or 0), 2),
            "median_risk_score": round(float(result.median_score or 0), 2)
        },
        "distribution": distribution,
        "top_risky_emails": [
            {
                "id": row.id,
                "sender": row.sender,
                "subject": row.subject,
                "risk_score": row.risk_score,
                "category": row.category,
                "received_at": row.received_at.isoformat() if row.received_at else None
            }
            for row in top_risky
        ]
    }


@router.get("/risk-trends")
async def get_risk_trends(
    days: int = 30,
    granularity: str = "day",
    db: Session = Depends(get_db)
):
    """
    Get risk score trends over time.
    
    Args:
        days: Number of days to include (default: 30)
        granularity: Time granularity (day, week) (default: day)
    
    Returns:
        Time series of risk scores
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # PostgreSQL date truncation
    if granularity == "week":
        trunc_func = func.date_trunc("week", Email.received_at)
    else:
        trunc_func = func.date_trunc("day", Email.received_at)
    
    stmt = select(
        trunc_func.label("period"),
        func.count(Email.id).label("count"),
        func.avg(Email.risk_score).label("avg_score"),
        func.max(Email.risk_score).label("max_score")
    ).where(
        Email.received_at >= cutoff_date
    ).group_by(
        "period"
    ).order_by(
        "period"
    )
    
    result = db.execute(stmt).all()
    
    return {
        "period": {
            "days": days,
            "granularity": granularity,
            "from": cutoff_date.isoformat(),
            "to": datetime.now(timezone.utc).isoformat()
        },
        "trends": [
            {
                "period": row.period.isoformat() if row.period else None,
                "email_count": row.count,
                "average_risk_score": round(float(row.avg_score or 0), 2),
                "max_risk_score": round(float(row.max_score or 0), 2)
            }
            for row in result
        ]
    }


@router.get("/health")
async def automation_health(db: Session = Depends(get_db)):
    """
    Check automation system health.
    
    Returns:
        Health status and statistics
    """
    # Check if risk scores are computed
    total_emails = db.execute(select(func.count(Email.id))).scalar()
    emails_with_scores = db.execute(
        select(func.count(Email.id)).where(Email.risk_score.isnot(None))
    ).scalar()
    
    # Check if features are populated
    emails_with_features = db.execute(
        select(func.count(Email.id)).where(Email.features_json.isnot(None))
    ).scalar()
    
    # Check last computed timestamp (from features_json)
    last_computed_stmt = select(Email.features_json).where(
        Email.features_json.isnot(None)
    ).order_by(Email.id.desc()).limit(1)
    
    last_features = db.execute(last_computed_stmt).scalar()
    last_computed = None
    if last_features and isinstance(last_features, dict):
        last_computed = last_features.get("computed_at")
    
    return {
        "status": "healthy" if emails_with_scores > 0 else "needs_computation",
        "statistics": {
            "total_emails": total_emails,
            "emails_with_risk_scores": emails_with_scores,
            "emails_with_features": emails_with_features,
            "coverage_percentage": round((emails_with_scores / total_emails * 100) if total_emails > 0 else 0, 2)
        },
        "last_computed": last_computed,
        "recommendations": [
            "Run /automation/recompute to compute risk scores"
        ] if emails_with_scores == 0 else []
    }
