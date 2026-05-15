"""Attack III — Cache Leakage (Li et al., arXiv:2605.11781 §4.4).

A shared caching proxy sits in front of an x402 origin. One paying
client primes the cache; N unpaid clients then request the same URL
with no X-PAYMENT header. We measure how many unpaid clients receive
the paid content.

Modes (server Cache-Control header on the paid response):
    none    — no Cache-Control     → proxy caches → 100% leak
    weak    — public, max-age=300   → proxy caches → 100% leak
    nostore — no-store, private    → proxy must not cache → 0% leak
"""

from __future__ import annotations

from typing import Literal

import aiohttp
from aiohttp import web

PAID_BODY = "PAID-CONTENT::confidential-risk-report::x402"
N_UNPAID = 100
Mode = Literal["none", "weak", "nostore"]


def _make_origin(mode: Mode, stats: dict) -> web.RequestHandler:
    async def handle(request: web.Request) -> web.Response:
        stats["origin_hits"] += 1
        if not request.headers.get("x-payment"):
            return web.Response(status=402, text="402 PAYMENT REQUIRED")
        stats["paid_served"] += 1
        headers = {"Content-Type": "text/plain"}
        if mode == "nostore":
            headers["Cache-Control"] = "no-store, private"
        elif mode == "weak":
            headers["Cache-Control"] = "public, max-age=300"
        # mode == "none" emits no Cache-Control
        return web.Response(status=200, text=PAID_BODY, headers=headers)

    return handle


def _make_proxy(origin_port: int, stats: dict) -> web.RequestHandler:
    """RFC-7234-ish caching proxy. Caches 200s unless told otherwise."""
    cache: dict[str, str] = {}

    async def handle(request: web.Request) -> web.Response:
        key = request.path_qs
        if key in cache:
            stats["proxy_hits"] += 1
            return web.Response(
                status=200,
                text=cache[key],
                headers={"Content-Type": "text/plain", "X-Cache": "HIT"},
            )
        stats["proxy_misses"] += 1
        fwd = {}
        if request.headers.get("x-payment"):
            fwd["x-payment"] = request.headers["x-payment"]
        async with (
            aiohttp.ClientSession() as session,
            session.get(f"http://127.0.0.1:{origin_port}{key}", headers=fwd) as resp,
        ):
            body = await resp.text()
            cc = (resp.headers.get("cache-control") or "").lower()
            cacheable = resp.status == 200 and "no-store" not in cc and "private" not in cc
            if cacheable:
                cache[key] = body
            return web.Response(
                status=resp.status,
                text=body,
                headers={"Content-Type": "text/plain", "X-Cache": "MISS"},
            )

    return handle


async def _start_server(handler: web.RequestHandler) -> tuple[web.AppRunner, int]:
    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]  # type: ignore[union-attr]
    return runner, port


async def _get(port: int, path: str, payment: str | None) -> tuple[int, str]:
    headers = {}
    if payment is not None:
        headers["x-payment"] = payment
    async with (
        aiohttp.ClientSession() as session,
        session.get(f"http://127.0.0.1:{port}{path}", headers=headers) as r,
    ):
        return r.status, await r.text()


async def _run_one_scenario(mode: Mode, n_unpaid: int) -> dict:
    origin_stats = {"origin_hits": 0, "paid_served": 0}
    origin_runner, origin_port = await _start_server(_make_origin(mode, origin_stats))
    proxy_stats = {"proxy_hits": 0, "proxy_misses": 0}
    proxy_runner, proxy_port = await _start_server(_make_proxy(origin_port, proxy_stats))

    try:
        # 1 paying client primes the cache
        await _get(proxy_port, "/paid-report", "valid-x402-payment-token")
        # N unpaid clients hit the same URL with NO payment
        leaks = 0
        for _ in range(n_unpaid):
            status, body = await _get(proxy_port, "/paid-report", None)
            if status == 200 and "PAID-CONTENT" in body:
                leaks += 1
    finally:
        await proxy_runner.cleanup()
        await origin_runner.cleanup()

    return {"leaks": leaks, "origin_hits": origin_stats["origin_hits"]}


async def simulate_cache(mode: Mode, trial_budget: int) -> dict:
    """Run cache-leak scenarios against the given Cache-Control mode.
    Trial budget is spent across scenarios of N_UNPAID probes each.
    """
    if mode not in ("none", "weak", "nostore"):
        raise ValueError(f"unknown cache_control mode: {mode}")

    scenarios = max(1, trial_budget // N_UNPAID)
    total_leaks = 0
    total_probes = 0
    total_origin_hits = 0
    for _ in range(scenarios):
        r = await _run_one_scenario(mode, N_UNPAID)
        total_leaks += r["leaks"]
        total_probes += N_UNPAID
        total_origin_hits += r["origin_hits"]

    return {
        "vector": "III",
        "paper_anchor": "arXiv:2605.11781 §4.4 + Table 3",
        "mode": mode,
        "leak_rate": round(total_leaks / total_probes, 4),
        "leaks": total_leaks,
        "probes": total_probes,
        "scenarios": scenarios,
        "origin_hits_total": total_origin_hits,
    }
