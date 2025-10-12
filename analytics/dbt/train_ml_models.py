from google.cloud import bigquery
import os

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r'D:\ApplyLens\analytics\dbt\applylens-ci.json'
client = bigquery.Client(project='applylens-gmail-1759983601')

print("🤖 Training BigQuery ML Models...")
print("This will take a few minutes as ARIMA models need to analyze time series data.\n")

# Train email count ARIMA model
print("1️⃣  Training m_email_count_arima...")
query = """
CREATE OR REPLACE MODEL `applylens.m_email_count_arima`
OPTIONS(
  MODEL_TYPE='ARIMA_PLUS',
  TIME_SERIES_TIMESTAMP_COL='d',
  TIME_SERIES_DATA_COL='emails',
  HOLIDAY_REGION='US',
  AUTO_ARIMA=TRUE,
  DATA_FREQUENCY='DAILY'
) AS
SELECT 
  d,
  emails
FROM `applylens.mrt_risk_daily`
WHERE d < CURRENT_DATE()
  AND emails IS NOT NULL
ORDER BY d
"""
job = client.query(query)
job.result()  # Wait for completion
print("   ✅ m_email_count_arima trained\n")

print("🎉 All ML models trained successfully!")
print("\n📊 You can now run forecasts:")
print("   dbt run --select pred_email_count --target dev --profiles-dir .")
