from fastapi import APIRouter, HTTPException, Depends, Request, Response
from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional, List, Literal, Dict, Any
import httpx
import os
import asyncio
import random

router = APIRouter()

DEVDIAG_BASE = os.getenv("DEVDIAG_BASE", "")
DEVDIAG_JWT = os.getenv("DEVDIAG_JWT", "")
DEVDIAG_ENABLED = os.getenv("DEVDIAG_ENABLED", "1") == "1"
TIMEOUT_S = int(os.getenv("DEVDIAG_TIMEOUT_S", "120"))
ALLOW = {
    h.strip().lower()
    for h in os.getenv(
        "DEVDIAG_ALLOW_HOSTS", "applylens.app,.applylens.app,api.applylens.app"
    ).split(",")
    if h.strip()
}

Preset = Literal["chat", "embed", "app", "full"]


class RunPayload(BaseModel):
    url: HttpUrl
    preset: Preset = "app"
    suppress: Optional[List[str]] = None
    tenant: str = "applylens"

    @field_validator("url")
    @classmethod
    def host_allowed(cls, v: HttpUrl) -> HttpUrl:
        host = v.host.lower()
        for pat in ALLOW:
            if pat.startswith("."):
                if host == pat[1:] or host.endswith(pat):
                    return v
            else:
                if host == pat:
                    return v
        raise ValueError(f"target host '{host}' not in allowlist")


class DiagResponse(BaseModel):
    ok: bool
    url: HttpUrl
    preset: Preset
    result: Dict[str, Any]


def require_base():
    if not DEVDIAG_BASE:
        raise HTTPException(status_code=503, detail="DevDiag base URL not configured")
    return True


def require_enabled():
    if not DEVDIAG_ENABLED:
        raise HTTPException(status_code=404, detail="Not found")
    return True


def _headers(req: Request) -> dict:
    h = {"content-type": "application/json"}
    if DEVDIAG_JWT:
        h["authorization"] = f"Bearer {DEVDIAG_JWT}"
    for k in ("x-request-id", "traceparent", "x-b3-traceid", "x-b3-spanid"):
        if v := req.headers.get(k):
            h[k] = v
    return h


_limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)


@router.get("/ops/diag/health")
async def diag_health(
    _: bool = Depends(require_base), __: bool = Depends(require_enabled)
):
    try:
        async with httpx.AsyncClient(
            timeout=10, follow_redirects=False, limits=_limits
        ) as c:
            r = await c.get(f"{DEVDIAG_BASE}/healthz")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"DevDiag health check failed: {e}")


async def _post_with_retry(
    url: str, json: dict, headers: dict, timeout: int
) -> httpx.Response:
    attempts = (
        (0.0, None),
        (0.6 + random.random() * 0.4, {429, 503, 504}),
        (1.5 + random.random() * 0.7, {429, 503, 504}),
    )
    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=False, limits=_limits
    ) as c:
        last = None
        for delay, retry_codes in attempts:
            if delay:
                await asyncio.sleep(delay)
            try:
                res = await c.post(url, json=json, headers=headers)
                if retry_codes and res.status_code in retry_codes:
                    last = res
                    continue
                return res
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last = e
        if isinstance(last, httpx.Response):
            raise HTTPException(status_code=last.status_code, detail=last.text)
        raise HTTPException(
            status_code=502, detail=f"DevDiag call failed: {last or 'retry exhausted'}"
        )


@router.post("/ops/diag", response_model=DiagResponse)
async def run_diag(
    payload: RunPayload,
    request: Request,
    _: bool = Depends(require_base),
    __: bool = Depends(require_enabled),
):
    h = _headers(request)
    r = await _post_with_retry(
        f"{DEVDIAG_BASE}/diag/run", payload.model_dump(), h, TIMEOUT_S
    )
    if int(r.headers.get("content-length") or "0") > 2_000_000:
        raise HTTPException(status_code=502, detail="DevDiag response too large")
    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    data = r.json()
    resp = Response()
    if rid := r.headers.get("x-request-id"):
        resp.headers["x-request-id"] = rid
    return DiagResponse.model_validate(data)
