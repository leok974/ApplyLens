"""
CLI script for generating weekly intelligence reports.

Usage:
    python -m app.eval.generate_report
    python -m app.eval.generate_report --output reports/weekly-report.md
    python -m app.eval.generate_report --slack https://hooks.slack.com/...
    python -m app.eval.generate_report --week 2024-01-15
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from ..database import SessionLocal
from .intelligence_report import ReportGenerator, format_report_as_html


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate weekly agent intelligence report"
    )

    parser.add_argument(
        "--week",
        type=str,
        help="Week start date (YYYY-MM-DD, Monday). Defaults to last Monday.",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path (markdown)",
    )

    parser.add_argument(
        "--html",
        type=str,
        help="Output HTML file path",
    )

    parser.add_argument(
        "--slack",
        type=str,
        help="Slack webhook URL to post report",
    )

    parser.add_argument(
        "--email",
        type=str,
        nargs="+",
        help="Email addresses to send report to",
    )

    parser.add_argument(
        "--format",
        choices=["markdown", "html", "both"],
        default="markdown",
        help="Output format (default: markdown)",
    )

    parser.add_argument(
        "--print",
        action="store_true",
        help="Print report to stdout",
    )

    return parser.parse_args()


def parse_week_start(week_str: str) -> datetime:
    """Parse week start date string."""
    try:
        dt = datetime.strptime(week_str, "%Y-%m-%d")
        # Ensure it's a Monday
        if dt.weekday() != 0:
            print(f"Warning: {week_str} is not a Monday. Using nearest Monday.")
            dt = dt - timedelta(days=dt.weekday())
        return dt
    except ValueError as e:
        print(f"Error parsing week date: {e}")
        sys.exit(1)


def send_email(
    report: str,
    recipients: list[str],
    subject: str = "Weekly Agent Intelligence Report",
):
    """
    Send report via email.

    Args:
        report: Report text (markdown or HTML)
        recipients: List of email addresses
        subject: Email subject line
    """
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        import os

        # Get SMTP settings from environment
        smtp_host = os.getenv("SMTP_HOST", "localhost")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        smtp_from = os.getenv("SMTP_FROM", "applylens@example.com")

        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_from
        msg["To"] = ", ".join(recipients)

        # Add HTML part (convert markdown if needed)
        if report.startswith("<!DOCTYPE") or report.startswith("<html"):
            html_part = MIMEText(report, "html")
        else:
            # Convert markdown to HTML
            html_content = format_report_as_html(report)
            html_part = MIMEText(html_content, "html")

        msg.attach(html_part)

        # Send email
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if smtp_user and smtp_password:
                server.starttls()
                server.login(smtp_user, smtp_password)
            server.send_message(msg)

        print(f"Report emailed to: {', '.join(recipients)}")

    except Exception as e:
        print(f"Error sending email: {e}")
        print("Email requires SMTP configuration (SMTP_HOST, SMTP_USER, SMTP_PASSWORD)")


def post_to_slack(report: str, webhook_url: str):
    """
    Post report to Slack.

    Args:
        report: Report text (markdown)
        webhook_url: Slack webhook URL
    """
    try:
        import requests

        # Slack has a 4000 char limit per message
        # Split into chunks if needed
        max_length = 3800  # Leave room for formatting

        if len(report) <= max_length:
            payload = {"text": report}
            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                print("Report posted to Slack")
            else:
                print(f"Failed to post to Slack: {response.status_code}")
        else:
            # Split into multiple messages
            chunks = []
            current_chunk = ""

            for line in report.split("\n"):
                if len(current_chunk) + len(line) + 1 > max_length:
                    chunks.append(current_chunk)
                    current_chunk = line
                else:
                    current_chunk += "\n" + line if current_chunk else line

            if current_chunk:
                chunks.append(current_chunk)

            print(f"Report split into {len(chunks)} messages")

            for i, chunk in enumerate(chunks, 1):
                header = f"*Part {i}/{len(chunks)}*\n\n" if len(chunks) > 1 else ""
                payload = {"text": header + chunk}
                response = requests.post(webhook_url, json=payload, timeout=10)
                if response.status_code != 200:
                    print(f"Failed to post chunk {i} to Slack: {response.status_code}")
                    break
            else:
                print("All parts posted to Slack successfully")

    except Exception as e:
        print(f"Error posting to Slack: {e}")


def main():
    """Main entry point."""
    args = parse_args()

    # Parse week start
    if args.week:
        week_start = parse_week_start(args.week)
    else:
        # Default to last Monday
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today - timedelta(days=today.weekday())

    print(f"Generating report for week of {week_start.strftime('%Y-%m-%d')}...")

    # Generate report
    db = SessionLocal()
    try:
        generator = ReportGenerator(db)
        report = generator.generate_weekly_report(week_start=week_start)

        # Print to stdout
        if args.print:
            print("\n" + "=" * 80)
            print(report)
            print("=" * 80)

        # Save markdown
        if args.output or args.format in ("markdown", "both"):
            output_path = (
                args.output
                or f"reports/weekly-report-{week_start.strftime('%Y-%m-%d')}.md"
            )
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                f.write(report)
            print(f"Markdown report saved to: {output_path}")

        # Save HTML
        if args.html or args.format in ("html", "both"):
            html_content = format_report_as_html(report)
            html_path = (
                args.html
                or f"reports/weekly-report-{week_start.strftime('%Y-%m-%d')}.html"
            )
            Path(html_path).parent.mkdir(parents=True, exist_ok=True)

            # Wrap in full HTML document
            full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Agent Intelligence Report - {week_start.strftime('%Y-%m-%d')}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
        }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; border-bottom: 2px solid #ecf0f1; padding-bottom: 8px; }}
        h3 {{ color: #7f8c8d; }}
        code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
        pre {{ background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        ul {{ padding-left: 25px; }}
        li {{ margin: 5px 0; }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""

            with open(html_path, "w") as f:
                f.write(full_html)
            print(f"HTML report saved to: {html_path}")

        # Post to Slack
        if args.slack:
            post_to_slack(report, args.slack)

        # Send email
        if args.email:
            send_email(report, args.email)

        print("\n✅ Report generation complete")

    finally:
        db.close()


if __name__ == "__main__":
    main()
