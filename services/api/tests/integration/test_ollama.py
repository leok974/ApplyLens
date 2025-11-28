import asyncio
import httpx
import os


async def test():
    OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://infra-ollama-1:11434").rstrip("/")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")

    print(f"OLLAMA_BASE: {OLLAMA_BASE}")
    print(f"OLLAMA_MODEL: {OLLAMA_MODEL}")

    url = f"{OLLAMA_BASE}/api/generate"
    body = {"model": OLLAMA_MODEL, "prompt": "Say hello", "stream": False}

    print(f"URL: {url}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("Sending request...")
            resp = await client.post(url, json=body)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                text = data.get("response", "NO RESPONSE KEY")
                print(f"Response: {text[:100]}")
            else:
                print(f"Error: {resp.text[:200]}")
    except Exception as e:
        print(f"Exception: {type(e).__name__}: {e}")


asyncio.run(test())
