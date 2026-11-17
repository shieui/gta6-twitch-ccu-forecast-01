"""gta6-twitch-ccu-forecast-01: forecast GTA VI's launch-day Twitch viewers, hour by hour.

Approach: launch-day shape from comparable launches, conditioned on the size of hour 1.

A launch's Twitch curve is driven by time zones unlocking through the day (rolling
midnight) and by the diurnal viewing cycle, so hours 2..24 are not a random walk from
hour 1 -- they follow a shape. The comparables in the case file are past big launches
with their full release-day hourly curves. For each comparable we form the log-ratio
of each hour's viewers to that launch's hour-1 viewers, and for each hour we regress
that log-ratio on the log of the launch's hour-1 viewers across the comparables.

That conditioning matters: across the comparables, a bigger hour 1 means a flatter
launch-day shape (correlation about -0.8 at the late hours -- a launch that is already
huge at 00:00 UTC has most of its audience in regions that unlocked early, so the
later US-driven rise is proportionally smaller). The regression captures it, so a
small launch is forecast a steep rise and a huge launch a nearly flat day.

Only clean comparables are used: the unlock notes tag some launches
early-access-contaminated or weak, and one entry is the target game's own pre-release
history (not a launch at all). A comparable also has to have a real launch hour 1:
if its hour-1 viewers are under 5% of its launch-day peak, the game had not unlocked
anywhere by 00:00 UTC (a simultaneous global unlock later in the day), so its ratio
to hour 1 is meaningless and it is dropped. That leaves 19 of the 38 comparables in
a practice case (23 in the final, which also holds the four practice launches).

The forecast for hour h is then:
    median  = p1 * exp(a_h + b_h * x),   x = log(p1) clamped to the comparables' range
    q_tau   = p1 * exp(a_h + b_h * x + z_tau * s_h)
where p1 is hour 1's print, (a_h, b_h) is the per-hour OLS fit, z_tau the standard
normal quantile at each level, and s_h the per-hour residual spread times 0.9 (a
floor of 0.15 keeps very tight hours honest). Clamping x to the comparables' range
keeps the forecast from extrapolating linearly past the biggest launches observed,
whose shapes are flat rather than declining.

Standard library only, no network, deterministic (no randomness, comparables sorted
by name, hours in order). Reads every <id>.in in the input directory and writes one
<id>.out per case, exactly as the starter did.
"""

import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path

# The grader's -P leaves /bot off sys.path: put it back first, so `import model` finds a model.py shipped beside this file.
sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.645, -0.674, 0, 0.674, 1.645]

# A comparable counts as a launch only if its hour-1 viewers are at least this
# fraction of its launch-day peak (below it, hour 1 was pre-unlock).
V1_FRACTION = 0.05
# The residual spread is scaled by this (leave-one-out over the comparables puts
# the optimum near 0.9; 1.0 over-covers slightly, 0.8 under-covers).
SD_MULT = 0.9
# The spread never goes below this, in log units.
SD_FLOOR = 0.15


def round2(x: float) -> float | int:
    """x rounded to 2 decimals, half up, as JavaScript's Math.round(x * 100) / 100 rounds it."""
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


def parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def tier_of(comp: dict) -> str:
    """The tier the case's unlock notes assign: clean, early-access-contaminated, weak, or target-history."""
    u = comp.get("unlock", "") or ""
    if "Tier: early-access-contaminated" in u:
        return "ea"
    if "Tier: weak" in u:
        return "weak"
    if "Tier: target-history" in u or "Not a launch" in u:
        return "target"
    return "clean"


def release_day_hours(comp: dict) -> dict[int, float]:
    """Map release-day hour (1..24) to viewers, from the comparable's hourly points."""
    day_start = parse_ts(comp["day_start"])
    by_hour: dict[int, float] = {}
    for row in comp.get("hourly", []):
        try:
            when = parse_ts(row["from"])
        except (KeyError, ValueError):
            continue
        dh = (when - day_start).total_seconds() / 3600.0
        if dh == int(dh) and 0 <= dh <= 23:
            viewers = row.get("viewers")
            if isinstance(viewers, (int, float)) and viewers > 0:
                by_hour[int(dh) + 1] = float(viewers)
    return by_hour


def select_comparables(case: dict) -> list[dict[int, float]]:
    """The comparables usable as launch-day shapes: clean launches with a real hour 1."""
    selected = []
    for comp in sorted(case.get("comparables", []), key=lambda c: c.get("name", "")):
        if tier_of(comp) != "clean":
            continue
        if "Grand Theft Auto VI" in (comp.get("name") or ""):
            continue
        by_hour = release_day_hours(comp)
        v1 = by_hour.get(1)
        if not v1:
            continue
        peak = max(by_hour.values())
        if peak <= 0 or v1 / peak < V1_FRACTION:
            continue
        selected.append(by_hour)
    return selected


def ols(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Ordinary least squares: returns (intercept, slope) for y ~ a + b*x."""
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return my, 0.0
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return my - b * mx, b


def forecast_case(case: dict, name: str) -> dict:
    if case["levels"] != LEVELS:
        raise ValueError(f"{name} asks for levels {case['levels']}, not {LEVELS}")
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour-1 print")
    p1 = max(1, first["viewers"])

    comps = select_comparables(case)
    if len(comps) < 3:
        # Too few usable comparables: fall back to the house baseline (persistence
        # with a widening spread), so the case is still valid.
        return {"hours": [{"hour": row["hour"], "q": [
            round2(p1 * math.exp(z * 0.15 * math.sqrt(row["hour"] - 1))) for z in Z]}
            for row in case["forecast"]]}

    log_v1 = [math.log(c[1]) for c in comps]
    lo_x, hi_x = min(log_v1), max(log_v1)
    # Clamp the target's log hour-1 to the comparables' range: the biggest launches
    # observed are flat, not declining, so do not extrapolate the slope past them.
    x = min(max(math.log(p1), lo_x), hi_x)

    hours = []
    for row in case["forecast"]:
        h = row["hour"]
        pts = [(math.log(c[1]), math.log(c[h] / c[1]))
               for c in comps if h in c and c[h] > 0]
        if len(pts) < 3:
            # Almost no comparable has this hour: hold at hour 1 with a wide spread.
            q = [round2(p1 * math.exp(z * 0.6)) for z in Z]
            hours.append({"hour": h, "q": q})
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        a, b = ols(xs, ys)
        mu = a + b * x
        resid = [y - (a + b * xx) for xx, y in pts]
        sd = math.sqrt(sum(r * r for r in resid) / max(len(resid) - 2, 1))
        sd = max(SD_FLOOR, sd * SD_MULT)
        q = []
        for z in Z:
            v = p1 * math.exp(mu + z * sd)
            v = min(max(v, 1.0), 1e9)
            q.append(round2(v))
        # Rounding can only tie adjacent quantiles, never invert them, but enforce it.
        for i in range(1, len(q)):
            if q[i] < q[i - 1]:
                q[i] = q[i - 1]
        hours.append({"hour": h, "q": q})
    return {"hours": hours}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
