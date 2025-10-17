"""
Golden tasks for insights.write agent.

These are representative test cases covering:
- Trend analysis
- Report generation
- Metric calculation
- Dashboard insights
"""
from typing import List
from app.eval.models import EvalTask, EvalSuite


def get_insights_tasks() -> List[EvalTask]:
    """Get all insights.write eval tasks."""
    return [
        # Trend analysis
        EvalTask(
            id="insights.trend.001",
            agent="insights.write",
            category="analysis",
            objective="Analyze email volume trends over the past 30 days",
            context={
                "time_range": "30d",
                "data_source": "elasticsearch",
                "metrics": ["email_count", "response_time", "categories"],
                "has_historical_data": True,
            },
            expected_output={
                "metrics_count": 5,
                "trends": ["volume_increase", "faster_response_time"],
                "has_summary": True,
                "has_recommendations": True,
            },
            invariants=["insights_data_quality"],
            difficulty="medium",
            tags=["trends", "analysis"],
        ),
        
        # Report generation
        EvalTask(
            id="insights.report.001",
            agent="insights.write",
            category="report",
            objective="Generate weekly productivity report",
            context={
                "time_range": "7d",
                "data_source": "bigquery",
                "report_type": "productivity",
                "include_charts": True,
            },
            expected_output={
                "metrics_count": 8,
                "trends": ["meeting_reduction", "email_efficiency"],
                "has_summary": True,
                "has_recommendations": True,
                "charts_generated": 3,
            },
            invariants=["insights_data_quality"],
            difficulty="easy",
            tags=["report", "productivity"],
        ),
        
        # Metric calculation
        EvalTask(
            id="insights.metric.001",
            agent="insights.write",
            category="analysis",
            objective="Calculate key email metrics for dashboard",
            context={
                "time_range": "24h",
                "data_source": "elasticsearch",
                "metrics": [
                    "total_emails",
                    "phishing_detected",
                    "avg_response_time",
                    "category_distribution",
                ],
            },
            expected_output={
                "metrics_count": 4,
                "trends": [],
                "has_summary": True,
                "has_recommendations": False,
            },
            invariants=["insights_data_quality"],
            difficulty="easy",
            tags=["metrics", "dashboard"],
        ),
        
        # Security analysis
        EvalTask(
            id="insights.security.001",
            agent="insights.write",
            category="analysis",
            objective="Analyze security incidents and risk patterns",
            context={
                "time_range": "90d",
                "data_source": "bigquery",
                "metrics": ["phishing_attempts", "high_risk_emails", "blocked_senders"],
                "include_anomalies": True,
            },
            expected_output={
                "metrics_count": 6,
                "trends": ["phishing_spike", "new_threat_vectors"],
                "has_summary": True,
                "has_recommendations": True,
                "anomalies_detected": 2,
            },
            invariants=["insights_data_quality"],
            difficulty="hard",
            tags=["security", "anomalies", "red_team"],
        ),
        
        # Comparison report
        EvalTask(
            id="insights.compare.001",
            agent="insights.write",
            category="analysis",
            objective="Compare current month vs previous month performance",
            context={
                "time_range": "60d",
                "data_source": "bigquery",
                "comparison_mode": "month_over_month",
                "metrics": ["email_volume", "response_time", "user_engagement"],
            },
            expected_output={
                "metrics_count": 6,
                "trends": ["volume_stable", "engagement_improved"],
                "has_summary": True,
                "has_recommendations": True,
                "comparison_included": True,
            },
            invariants=["insights_data_quality"],
            difficulty="medium",
            tags=["comparison", "trends"],
        ),
        
        # Edge case: insufficient data
        EvalTask(
            id="insights.edge.001",
            agent="insights.write",
            category="edge_case",
            objective="Generate insights with minimal data",
            context={
                "time_range": "1d",
                "data_source": "elasticsearch",
                "metrics": ["email_count"],
                "has_historical_data": False,
                "data_points": 5,
            },
            expected_output={
                "metrics_count": 1,
                "trends": [],
                "has_summary": True,
                "has_recommendations": False,
                "data_quality_warning": True,
            },
            invariants=[],
            difficulty="medium",
            tags=["edge_case", "data_quality"],
        ),
        
        # Real-time dashboard
        EvalTask(
            id="insights.realtime.001",
            agent="insights.write",
            category="analysis",
            objective="Generate real-time dashboard metrics",
            context={
                "time_range": "1h",
                "data_source": "elasticsearch",
                "metrics": ["current_email_rate", "active_users", "system_health"],
                "refresh_rate": "5m",
            },
            expected_output={
                "metrics_count": 3,
                "trends": [],
                "has_summary": False,
                "has_recommendations": False,
                "real_time": True,
            },
            invariants=["insights_data_quality"],
            difficulty="easy",
            tags=["realtime", "dashboard"],
        ),
        
        # Comprehensive quarterly report
        EvalTask(
            id="insights.quarterly.001",
            agent="insights.write",
            category="report",
            objective="Generate comprehensive quarterly business review",
            context={
                "time_range": "90d",
                "data_source": "bigquery",
                "report_type": "quarterly_review",
                "metrics": [
                    "total_emails",
                    "productivity_metrics",
                    "security_incidents",
                    "user_growth",
                    "system_performance",
                ],
                "include_charts": True,
                "include_forecasts": True,
            },
            expected_output={
                "metrics_count": 12,
                "trends": [
                    "steady_growth",
                    "improved_security",
                    "performance_stable",
                ],
                "has_summary": True,
                "has_recommendations": True,
                "charts_generated": 8,
                "forecasts_included": True,
            },
            invariants=["insights_data_quality"],
            difficulty="hard",
            tags=["quarterly", "comprehensive", "forecasts"],
        ),
    ]


def get_insights_suite() -> EvalSuite:
    """Get the complete insights.write eval suite."""
    suite = EvalSuite(
        name="insights_write_v1",
        agent="insights.write",
        version="1.0",
        tasks=get_insights_tasks(),
        invariants=["insights_data_quality"],
    )
    return suite
