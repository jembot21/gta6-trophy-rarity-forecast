"""Standard-library deterministic trophy earn-rate quantile forecasts."""

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from statistics import NormalDist, mean, median


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def timestamp(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def logit(rate):
    p = clamp(rate, 0.01, 99.99) / 100
    return math.log(p) - math.log1p(-p)


def inv_logit(v):
    if v >= 0:
        return 100 / (1 + math.exp(-v))
    e = math.exp(v)
    return 100 * e / (1 + e)


def round4(v):
    return math.floor(v * 10000 + 0.5) / 10000


def rates(read):
    value = read.get("rates")
    return value if isinstance(value, list) else []


def rate_at(read, i):
    values = rates(read)
    return values[i] if i < len(values) else None


def distinct_reads(case):
    kept, previous = [], None
    for read in case.get("history", []):
        key = (read["players_tracked"], tuple(rates(read)))
        if key != previous:
            kept.append(read)
            previous = key
    return kept


def slope(points):
    mx = mean(x for x, _ in points)
    my = mean(y for _, y in points)
    denominator = sum((x - mx) ** 2 for x, _ in points)
    return sum((x - mx) * (y - my) for x, y in points) / denominator if denominator else 0.0


def forecast_details(case):
    reads = distinct_reads(case)
    release = timestamp(case["game"]["release_date"].split("T")[0])

    def axis(at):
        hours = (timestamp(at) - release).total_seconds() / 3600
        # Preserve pre-release reads within the logarithm's valid domain.
        # Earlier malformed dates saturate just above its singularity.
        return math.log1p(max(-1.0 + 1e-12, hours))

    xs = [axis(read["at"]) for read in reads]
    target_x = axis(case["target"])
    last_players = reads[-1]["players_tracked"] if reads else 0
    players = last_players
    if len({r["players_tracked"] for r in reads}) >= 2:
        points = list(zip(xs, (r["players_tracked"] for r in reads)))
        fitted = mean(y for _, y in points) + slope(points) * (target_x - mean(xs))
        players = clamp(fitted, last_players, 50 * last_players)
    observations, slopes = [], []
    for i in range(len(case["trophies"])):
        points = [(x, rate_at(r, i) / 100 * r["players_tracked"])
                  for x, r in zip(xs, reads) if rate_at(r, i) is not None]
        observations.append(points)
        slopes.append(slope(points) if len(points) >= 3 else None)
    fitted_slopes = [b for b in slopes if b is not None]
    pooled = mean(fitted_slopes) if fitted_slopes else 0.0
    estimates, growth = [], []
    for points, b in zip(observations, slopes):
        estimate = None
        if b is not None:
            w = len(points) / (len(points) + 0.25)
            shrunk = w * b + (1 - w) * pooled
            last_x, last_earners = points[-1]
            estimate = last_earners + shrunk * (target_x - last_x)
            if last_earners > 0:
                growth.append(clamp(estimate / last_earners - 1, 0, 3))
        estimates.append(estimate)
    pooled_growth = median(growth) if growth else 0.0
    changes = []
    for old, new in zip(reads, reads[1:]):
        days = (timestamp(new["at"]) - timestamp(old["at"])).total_seconds() / 86400
        for i in range(len(case["trophies"])):
            a, b = rate_at(old, i), rate_at(new, i)
            if a is not None and b is not None:
                changes.append(abs(logit(b) - logit(a)) / math.sqrt(max(days, 1 / 24)))
    vol = math.sqrt(mean(v * v for v in changes)) if changes else 0.0
    amplitude = clamp(vol, 0.35, 0.45)
    days = max(0.0, case["horizon_minutes"] / 1440)
    stale = 0.35 if len(reads) < 2 else 0.0
    zs = [NormalDist().inv_cdf(level) for level in case["levels"]]
    rows, sigmas, medians = [], [], []
    for i, trophy in enumerate(case["trophies"]):
        points = observations[i]
        center = 0.01
        if points and players > 0:
            last_earners = points[-1][1]
            estimate = estimates[i]
            if estimate is None:
                estimate = last_earners * (1 + pooled_growth)
            center = clamp(100 * clamp(estimate, last_earners, players) / players, 0.01, 99.99)
        last_rate = rate_at(reads[-1], i) if reads else None
        sigma = 2.0 if last_rate is None else max(0.05, math.sqrt(
            amplitude ** 2 * days + (0.5 * abs(logit(center) - logit(last_rate))) ** 2
            + stale ** 2 * days))
        quantiles = []
        for z in zs:
            q = clamp(round4(inv_logit(logit(center) + z * sigma)), 0, 100)
            quantiles.append(max(q, quantiles[-1] if quantiles else 0))
        rows.append({"id": trophy["id"], "q": quantiles})
        sigmas.append(sigma)
        medians.append(center)
    rows.sort(key=lambda row: row["id"])
    return {"trophies": rows}, sigmas, medians


def main():
    source = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
    destination = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    destination.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        result, _, _ = forecast_details(case)
        encoded = json.dumps(result, separators=(",", ":"), allow_nan=False) + "\n"
        (destination / (str(case["id"]) + ".out")).write_text(encoded, encoding="utf-8")


if __name__ == "__main__":
    main()
