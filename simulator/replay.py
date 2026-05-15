"""Attack II — Replay Overgrant (Li et al., arXiv:2605.11781).

The same signed X-PAYMENT is replayed N times concurrently against an
endpoint operating in one of three dedup modes:
    naive  — no dedup at all                       (DGR ≈ N)
    racy   — check-then-act with a non-atomic gap   (partial overgrant)
    atomic — synchronous claim before any await     (DGR = 1)

Each "trial" stands up a fresh aiohttp server, fires N concurrent
requests, counts HTTP 200 responses, and tears the server down. The
trial budget is split across the N_VALUES fan-out so each (mode, N)
pair gets approximately budget / |N_VALUES| trials.

Paper notation: DGR (duplicate-grant rate, §2.4 Definition 3).
"""

from __future__ import annotations

import asyncio
from typing import Literal

import aiohttp
from aiohttp import web

PAY_ID = "pay_0xA1B2C3D4E5F6"
N_VALUES: tuple[int, ...] = (1, 10, 50, 200, 500)
Mode = Literal["naive", "racy", "atomic"]


def _make_handler(mode: Mode, state: dict) -> web.RequestHandler:
    """Build a request handler that implements one of the three dedup modes."""

    async def handle(request: web.Request) -> web.Response:
        pay_id = request.headers.get("x-payment", "")
        granted: set[str] = state["granted"]
        do_grant = False
        if mode == "naive":
            do_grant = True
        elif mode == "racy":
            seen = pay_id in granted
            await asyncio.sleep(0.001)  # non-atomic gap — races under load
            if not seen:
                granted.add(pay_id)
                do_grant = True
        elif mode == "atomic":
            if pay_id not in granted:
                granted.add(pay_id)
                do_grant = True
        else:
            raise ValueError(f"unknown idempotency mode: {mode}")

        if do_grant:
            state["grants"] += 1
            return web.Response(status=200, text="GRANTED")
        return web.Response(status=409, text="DUPLICATE")

    return handle


async def _run_one_trial(mode: Mode, n: int) -> int:
    """Spin up a server, fire N concurrent replays, return grant count."""
    state = {"granted": set(), "grants": 0}
    app = web.Application()
    app.router.add_route("*", "/", _make_handler(mode, state))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]  # type: ignore[union-attr]

    try:
        connector = aiohttp.TCPConnector(limit=0, force_close=True)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [
                session.get(f"http://127.0.0.1:{port}/", headers={"x-payment": PAY_ID})
                for _ in range(n)
            ]
            responses = await asyncio.gather(*tasks)
            # Drain so the server can close cleanly.
            for r in responses:
                await r.read()
                r.release()
    finally:
        await runner.cleanup()

    return state["grants"]


async def simulate_replay(mode: Mode, trial_budget: int) -> dict:
    """Run Attack II against an endpoint in `mode`.

    Trial budget is split evenly across N_VALUES. Returns paper-aligned
    DGR metrics.
    """
    if mode not in ("naive", "racy", "atomic"):
        raise ValueError(f"unknown idempotency mode: {mode}")

    trials_per_n = max(1, trial_budget // len(N_VALUES))
    points = []
    total_grants = 0
    total_settlements = 0

    for n in N_VALUES:
        runs = []
        for _ in range(trials_per_n):
            grants = await _run_one_trial(mode, n)
            runs.append(grants)
        mean = sum(runs) / len(runs)
        points.append(
            {
                "n_replays": n,
                "trials": trials_per_n,
                "DGR_mean": round(mean, 2),
                "DGR_max": max(runs),
            }
        )
        total_grants += sum(runs)
        total_settlements += len(runs)  # each trial = 1 intended settlement

    return {
        "vector": "II",
        "paper_anchor": "arXiv:2605.11781 Table 1 + §4.3 + Definition 3",
        "mode": mode,
        "points": points,
        "DGR_overall": round(total_grants / total_settlements, 2),
        "settlements": total_settlements,
    }
