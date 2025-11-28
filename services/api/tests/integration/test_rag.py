import os

os.environ["ELASTICSEARCH_URL"] = "http://applylens-es-prod:9200"

from elasticsearch import Elasticsearch
from app.core.rag import rag_search
from app.core.mail_tools import find_emails

es = Elasticsearch("http://applylens-es-prod:9200")
rag = rag_search(
    es, "Show me all emails", {}, k=5, owner_email="leoklemet.pa@gmail.com"
)

print("RAG result:")
print(f'  Total: {rag.get("total")}')
print(f'  Docs count: {len(rag.get("docs", []))}')
if rag.get("docs"):
    print(f'  First doc has keys: {list(rag["docs"][0].keys())}')
    print(f'  First doc subject: {rag["docs"][0].get("subject", "N/A")}')

answer, actions = find_emails(rag, "Show me all emails")
print("\nTool answer:")
print(answer)
