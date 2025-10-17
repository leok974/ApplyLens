"""
Insights Writer Agent - Phase 3 PR3

Queries warehouse metrics and generates markdown weekly reports.
Practical use case: Automated insights reports for email activity, application trends.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from ..providers.factory import get_provider_factory
from ..utils.artifacts import artifacts_store


class InsightsWriterAgent:
    """
    Generate weekly insights reports from warehouse data.
    
    Workflow:
    1. Query BigQuery for weekly aggregated metrics
    2. Analyze trends (week-over-week changes)
    3. Generate markdown report with tables and insights
    4. Write to artifacts with ISO week path (2024-W03.md)
    
    Use cases:
    - Weekly email activity summaries
    - Application pipeline reports
    - Performance trend analysis
    - Executive summaries
    
    Safety:
    - Read-only queries (always allowed)
    - No action gates required
    - Reports written to artifacts only
    """
    
    NAME = "insights_writer"
    
    def __init__(self, provider_factory=None):
        """Initialize with provider factory."""
        self.factory = provider_factory or get_provider_factory()
    
    def describe(self) -> Dict[str, Any]:
        """Return agent description."""
        return {
            "name": self.NAME,
            "description": "Generate weekly insights reports from warehouse metrics",
            "capabilities": [
                "Query warehouse for aggregated metrics",
                "Analyze week-over-week trends",
                "Generate markdown reports",
                "Create tables and charts",
                "Write weekly artifacts"
            ],
            "safe_by_default": True,
            "requires_approval": []  # Read-only, no approvals needed
        }
    
    def plan(self, objective: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create execution plan."""
        report_type = params.get('report_type', 'email_activity')  # email_activity, applications, etc.
        week_offset = params.get('week_offset', 0)  # 0 = current week, -1 = last week
        include_charts = params.get('include_charts', True)
        
        steps = [
            f"1. Calculate ISO week for offset {week_offset}",
            f"2. Query warehouse metrics: {report_type}",
            "3. Query previous week for comparison",
            "4. Calculate trends (week-over-week %)",
            "5. Generate markdown report with tables",
        ]
        
        if include_charts:
            steps.append("6. Include markdown charts (sparklines)")
        
        steps.append(f"7. Write report artifact: {report_type}-YYYY-Wxx.md")
        
        return {
            "agent": self.NAME,
            "objective": objective,
            "steps": steps,
            "tools": ["bigquery"],
            "report_type": report_type,
            "week_offset": week_offset,
            "include_charts": include_charts
        }
    
    def execute(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute insights report generation.
        
        Returns:
            Dict with report metadata and artifacts
        """
        report_type = plan.get('report_type', 'email_activity')
        week_offset = plan.get('week_offset', 0)
        include_charts = plan.get('include_charts', True)
        
        ops_count = 0
        
        # Calculate ISO week
        target_date = datetime.now() + timedelta(weeks=week_offset)
        iso_year, iso_week, _ = target_date.isocalendar()
        week_label = f"{iso_year}-W{iso_week:02d}"
        
        # Get warehouse provider
        bq = self.factory.bigquery()
        
        # Query current week metrics
        current_metrics = self._query_metrics(bq, report_type, iso_year, iso_week)
        ops_count += 1
        
        # Query previous week for comparison
        prev_date = target_date - timedelta(weeks=1)
        prev_year, prev_week, _ = prev_date.isocalendar()
        previous_metrics = self._query_metrics(bq, report_type, prev_year, prev_week)
        ops_count += 1
        
        # Calculate trends
        trends = self._calculate_trends(current_metrics, previous_metrics)
        
        # Generate markdown report
        report = self._generate_report(
            report_type=report_type,
            week_label=week_label,
            current=current_metrics,
            previous=previous_metrics,
            trends=trends,
            include_charts=include_charts
        )
        
        # Write artifact with weekly path
        artifact_path = artifacts_store.get_weekly_path(
            prefix=report_type,
            extension="md"
        )
        artifacts_store.write(
            artifact_path,
            report,
            agent_name=self.NAME
        )
        
        # Also write JSON data
        json_artifact = {
            'report_type': report_type,
            'week': week_label,
            'timestamp': plan.get('started_at', ''),
            'current_metrics': current_metrics,
            'previous_metrics': previous_metrics,
            'trends': trends
        }
        
        json_path = artifacts_store.get_weekly_path(
            prefix=report_type,
            extension="json"
        )
        artifacts_store.write_json(
            json_path,
            json_artifact,
            agent_name=self.NAME
        )
        
        return {
            'report_type': report_type,
            'week': week_label,
            'artifacts': {
                'report': artifact_path,
                'data': json_path
            },
            'metrics_summary': {
                'current': current_metrics,
                'trends': trends
            },
            'ops_count': ops_count
        }
    
    def _query_metrics(
        self, 
        bq, 
        report_type: str, 
        year: int, 
        week: int
    ) -> Dict[str, Any]:
        """Query warehouse for weekly metrics."""
        
        if report_type == 'email_activity':
            query = f"""
                SELECT
                    COUNT(*) as total_emails,
                    COUNT(DISTINCT sender) as unique_senders,
                    COUNTIF(has_attachment = TRUE) as emails_with_attachments,
                    COUNTIF(is_spam = TRUE) as spam_emails,
                    AVG(LENGTH(body_text)) as avg_email_length
                FROM `analytics.emails_raw`
                WHERE EXTRACT(YEAR FROM received_at) = {year}
                  AND EXTRACT(ISOWEEK FROM received_at) = {week}
            """
        elif report_type == 'applications':
            query = f"""
                SELECT
                    COUNT(*) as total_applications,
                    COUNT(DISTINCT company) as unique_companies,
                    COUNTIF(status = 'interview') as interviews,
                    COUNTIF(status = 'offer') as offers,
                    COUNTIF(status = 'rejected') as rejections
                FROM `analytics.applications`
                WHERE EXTRACT(YEAR FROM applied_at) = {year}
                  AND EXTRACT(ISOWEEK FROM applied_at) = {week}
            """
        else:
            return {}
        
        rows = bq.query_rows(query)
        return rows[0] if rows else {}
    
    def _calculate_trends(
        self, 
        current: Dict[str, Any], 
        previous: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate week-over-week trends."""
        trends = {}
        
        for key in current.keys():
            curr_val = current.get(key, 0)
            prev_val = previous.get(key, 0)
            
            if prev_val == 0:
                change_pct = 100.0 if curr_val > 0 else 0.0
            else:
                change_pct = ((curr_val - prev_val) / prev_val) * 100
            
            trends[key] = {
                'current': curr_val,
                'previous': prev_val,
                'change': curr_val - prev_val,
                'change_pct': round(change_pct, 1),
                'direction': '📈' if change_pct > 0 else '📉' if change_pct < 0 else '➡️'
            }
        
        return trends
    
    def _generate_report(
        self,
        report_type: str,
        week_label: str,
        current: Dict[str, Any],
        previous: Dict[str, Any],
        trends: Dict[str, Dict[str, Any]],
        include_charts: bool
    ) -> str:
        """Generate markdown report."""
        report = []
        
        # Header
        report.append(f"# Weekly Insights Report: {report_type.replace('_', ' ').title()}\n")
        report.append(f"**Week**: {week_label}\n")
        report.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        report.append("---\n\n")
        
        # Executive Summary
        report.append("## Executive Summary\n\n")
        
        if report_type == 'email_activity':
            total = current.get('total_emails', 0)
            spam = current.get('spam_emails', 0)
            spam_pct = (spam / total * 100) if total > 0 else 0
            
            report.append(f"- Processed **{total:,}** emails this week\n")
            report.append(f"- From **{current.get('unique_senders', 0):,}** unique senders\n")
            report.append(f"- Spam rate: **{spam_pct:.1f}%** ({spam:,} spam emails)\n")
            report.append(f"- Emails with attachments: **{current.get('emails_with_attachments', 0):,}**\n\n")
        
        elif report_type == 'applications':
            report.append(f"- Submitted **{current.get('total_applications', 0):,}** applications\n")
            report.append(f"- To **{current.get('unique_companies', 0):,}** unique companies\n")
            report.append(f"- Scheduled **{current.get('interviews', 0):,}** interviews\n")
            report.append(f"- Received **{current.get('offers', 0):,}** offers\n\n")
        
        # Trends Table
        report.append("## Week-Over-Week Trends\n\n")
        report.append("| Metric | Current | Previous | Change | % Change |\n")
        report.append("|--------|---------|----------|--------|----------|\n")
        
        for key, trend in trends.items():
            metric_name = key.replace('_', ' ').title()
            current_val = self._format_value(trend['current'])
            previous_val = self._format_value(trend['previous'])
            change = trend['change']
            change_pct = trend['change_pct']
            direction = trend['direction']
            
            report.append(
                f"| {metric_name} | {current_val} | {previous_val} | "
                f"{change:+,} | {direction} {change_pct:+.1f}% |\n"
            )
        
        report.append("\n")
        
        # Charts (sparklines in markdown)
        if include_charts:
            report.append("## Visual Trends\n\n")
            report.append("```\n")
            
            for key, trend in list(trends.items())[:3]:  # Show top 3 metrics
                metric_name = key.replace('_', ' ').title()
                # Simple ASCII sparkline
                curr = trend['current']
                prev = trend['previous']
                max_val = max(curr, prev, 1)
                
                bars_curr = int((curr / max_val) * 20)
                bars_prev = int((prev / max_val) * 20)
                
                report.append(f"{metric_name:30s} Prev: {'█' * bars_prev}\n")
                report.append(f"{' ' * 30} Curr: {'█' * bars_curr}\n\n")
            
            report.append("```\n\n")
        
        # Key Insights
        report.append("## Key Insights\n\n")
        
        # Find biggest movers
        biggest_increase = max(trends.items(), key=lambda x: x[1]['change_pct'], default=None)
        biggest_decrease = min(trends.items(), key=lambda x: x[1]['change_pct'], default=None)
        
        if biggest_increase and biggest_increase[1]['change_pct'] > 10:
            metric = biggest_increase[0].replace('_', ' ')
            pct = biggest_increase[1]['change_pct']
            report.append(f"- 📈 **{metric.title()}** increased significantly by **{pct:.1f}%**\n")
        
        if biggest_decrease and biggest_decrease[1]['change_pct'] < -10:
            metric = biggest_decrease[0].replace('_', ' ')
            pct = abs(biggest_decrease[1]['change_pct'])
            report.append(f"- 📉 **{metric.title()}** decreased by **{pct:.1f}%**\n")
        
        report.append("\n")
        
        # Footer
        report.append("---\n\n")
        report.append("*Generated automatically by InsightsWriterAgent*\n")
        
        return ''.join(report)
    
    def _format_value(self, value: Any) -> str:
        """Format value for display."""
        if isinstance(value, float):
            if value >= 1000:
                return f"{value:,.0f}"
            return f"{value:.1f}"
        elif isinstance(value, int):
            return f"{value:,}"
        return str(value)


def register(registry):
    """Register Insights Writer Agent."""
    agent = InsightsWriterAgent()
    
    def handler(plan: Dict[str, Any]) -> Dict[str, Any]:
        return agent.execute(plan)
    
    registry.register(agent.NAME, handler)
