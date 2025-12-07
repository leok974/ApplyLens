# Test LLM-Powered Resume Upload
# Verifies that resume upload extracts profile data using LLM

Write-Host "🧪 Testing LLM-Powered Resume Upload..." -ForegroundColor Cyan

# Create sample resume text
$resumeContent = @"
Leo Klemet
AI/ML Engineer & Full-Stack Developer
Herndon, VA, US

Email: leoklemet.pa@gmail.com
Phone: 202-440-1027
GitHub: https://github.com/leok974
Portfolio: https://www.leoklemet.com
LinkedIn: https://linkedin.com/in/leoklemet

SUMMARY
Experienced AI/ML engineer specializing in agentic systems and full-stack development.
8+ years building production systems with Python, FastAPI, React, and modern ML frameworks.
Passionate about creating intelligent automation that enhances developer productivity.

SKILLS
Python, FastAPI, React, TypeScript, PostgreSQL, Elasticsearch, Docker, Kubernetes,
LLMs, LangChain, LangGraph, OpenAI, Ollama, Prometheus, Grafana, Redis, SQLAlchemy,
Pydantic, Pytest, Playwright, GitHub Actions, Datadog

EXPERIENCE
Senior AI Engineer | ApplyLens | 2023 - Present
- Built agentic job-inbox with Gmail OAuth integration and intelligent email parsing
- Implemented LLM-powered form completion for browser extension (gpt-4o-mini)
- Designed Elasticsearch search with synonym/recency boosts and role matching
- Created Prometheus/Grafana metrics + alerting for system health monitoring
- Developed policy engine for budget tracking and approval workflows

Full-Stack Engineer | TechCorp | 2018 - 2023
- Architected microservices backend with FastAPI and PostgreSQL
- Built React dashboards for real-time analytics and monitoring
- Implemented CI/CD pipelines with Docker and Kubernetes
- Mentored junior engineers and led code reviews

PROJECTS
ApplyLens - Agentic job-inbox that ingests Gmail, tracks applications, and adds security risk scoring
SiteAgent - Self-updating portfolio & SEO agent that ships diff-based approvals
"@

# Save to temporary file
$tempFile = [System.IO.Path]::GetTempFileName()
$pdfFile = $tempFile.Replace(".tmp", ".txt")
$resumeContent | Out-File -FilePath $pdfFile -Encoding UTF8
Write-Host "📄 Created sample resume: $pdfFile" -ForegroundColor Green

# Note: This test requires authentication
# In production, you'd use a valid auth token
Write-Host ""
Write-Host "⚠️  Manual Test Required:" -ForegroundColor Yellow
Write-Host "   1. Upload resume via ApplyLens UI at http://localhost:8003"
Write-Host "   2. Or use the /api/resume/upload endpoint with auth token"
Write-Host "   3. Check logs for: 'LLM extracted profile: X skills, Leo Klemet'"
Write-Host "   4. Verify /api/resume/current returns populated fields"
Write-Host ""

Write-Host "🔍 Expected LLM Extraction:" -ForegroundColor Cyan
Write-Host "   ✅ full_name: Leo Klemet"
Write-Host "   ✅ headline: AI/ML Engineer & Full-Stack Developer"
Write-Host "   ✅ location: Herndon, VA, US"
Write-Host "   ✅ years_experience: 8"
Write-Host "   ✅ skills: ~20+ technical skills"
Write-Host "   ✅ top_roles: [AI Engineer, ML Engineer, Full-Stack Engineer]"
Write-Host "   ✅ github_url: https://github.com/leok974"
Write-Host "   ✅ portfolio_url: https://www.leoklemet.com"
Write-Host "   ✅ linkedin_url: https://linkedin.com/in/leoklemet"
Write-Host "   ✅ summary: 2-4 sentence professional summary"
Write-Host ""

Write-Host "📊 Verification Commands:" -ForegroundColor Cyan
Write-Host "   # Check API logs for LLM extraction"
Write-Host "   docker logs applylens-api-prod | Select-String 'LLM extracted'"
Write-Host ""
Write-Host "   # View current resume profile"
Write-Host "   Invoke-RestMethod -Uri 'http://localhost:8003/api/resume/current' | ConvertTo-Json -Depth 5"
Write-Host ""
Write-Host "   # Check extension profile endpoint"
Write-Host "   Invoke-RestMethod -Uri 'http://localhost:8003/api/profile/me' | ConvertTo-Json -Depth 5"
Write-Host ""

Write-Host "✅ Sample resume ready at: $pdfFile" -ForegroundColor Green
Write-Host "📋 Next: Upload this file via UI or API to test LLM extraction" -ForegroundColor Magenta
