"""Deterministic trophy rarity forecasts from tracked players and earner counts.

Python 3.10+, standard library only. Input and output directories are selected
by MAKEFUN_INPUT_DIR and MAKEFUN_OUTPUT_DIR, defaulting to /input and /output.
"""

import json
import math
import os
from pathlib import Path
import statistics
from datetime import datetime, timezone


def clamp(value, low=0.01, high=99.99):
    return min(high, max(low, value))


def logit(rate):
    rate = clamp(rate)
    return math.log(rate / (100.0 - rate))


def inv_logit(value):
    if value >= 0:
        return 100.0 / (1.0 + math.exp(-value))
    exp_value = math.exp(value)
    return 100.0 * exp_value / (1.0 + exp_value)


def round4(value):
    return math.floor(value * 10000.0 + 0.5) / 10000.0


def parse_time(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def release_time(case):
    return datetime.combine(
        datetime.fromisoformat(case['game']['release_date']).date(),
        datetime.min.time(), tzinfo=timezone.utc,
    )


def time_x(timestamp, release):
    hours = (parse_time(timestamp) - release).total_seconds() / 3600.0
    return math.log1p(max(hours, 0.0))


def distinct_reads(case):
    kept = []
    previous = None
    for read in case['history']:
        key = (read['players_tracked'], tuple(read.get('rates') or ()))
        if not kept or key != previous:
            kept.append(read)
            previous = key
    return kept


def load_case(path):
    return json.loads(path.read_text(encoding='utf-8'))


def slope(points):
    mean_x = statistics.mean(x for x, _ in points)
    mean_y = statistics.mean(y for _, y in points)
    denominator = sum((x - mean_x) ** 2 for x, _ in points)
    if denominator == 0:
        return 0.0
    return sum((x - mean_x) * (y - mean_y) for x, y in points) / denominator


def count_forecasts(case, reads):
    release = release_time(case)
    xs = [time_x(read['at'], release) for read in reads]
    target_x = time_x(case['target'], release)
    players = [read['players_tracked'] for read in reads]
    last_players = players[-1]
    predicted_players = last_players
    if len(set(players)) >= 2:
        points = list(zip(xs, players))
        b = slope(points)
        a = statistics.mean(players) - b * statistics.mean(xs)
        predicted_players = clamp(a + b * target_x, last_players, 50 * last_players)

    observations = []
    last_rates = []
    slopes = []
    for i in range(len(case['trophies'])):
        obs = []
        last_rate = None
        for x, read in zip(xs, reads):
            rates = read.get('rates') or ()
            if i >= len(rates):
                continue
            rate = rates[i]
            if rate is not None:
                obs.append((x, rate / 100.0 * read['players_tracked']))
                last_rate = rate
        observations.append(obs)
        last_rates.append(last_rate)
        slopes.append(slope(obs) if len(obs) >= 3 else None)

    fitted_slopes = [b for b in slopes if b is not None]
    pooled_slope = statistics.mean(fitted_slopes) if fitted_slopes else 0.0
    fits = []
    growth = []
    for obs, b in zip(observations, slopes):
        if b is None:
            fits.append(None)
            continue
        weight = len(obs) / (len(obs) + 0.25)
        shrunk = weight * b + (1.0 - weight) * pooled_slope
        fitted = obs[-1][1] + shrunk * (target_x - obs[-1][0])
        fits.append(fitted)
        last_count = obs[-1][1]
        growth.append(clamp(fitted / last_count - 1.0, 0.0, 3.0)
                      if last_count else 0.0)
    pooled_growth = statistics.median(growth) if growth else 0.0
    medians = []
    for obs, fitted in zip(observations, fits):
        if not obs:
            medians.append(0.01)
            continue
        last_count = obs[-1][1]
        estimate = fitted if fitted is not None else last_count * (1 + pooled_growth)
        estimate = clamp(estimate, last_count, predicted_players)
        medians.append(clamp(100.0 * estimate / predicted_players))
    return medians, last_rates


def forecast_details(case):
    reads = distinct_reads(case)
    medians, last_rates = count_forecasts(case, reads)
    volatility = []
    for before, after in zip(reads, reads[1:]):
        days = (parse_time(after['at']) - parse_time(before['at'])).total_seconds() / 86400.0
        scale = math.sqrt(max(days, 1.0 / 24.0))
        for old, new in zip(before.get('rates') or (), after.get('rates') or ()):
            if old is not None and new is not None:
                volatility.append(abs(logit(new) - logit(old)) / scale)
    pooled_vol = math.sqrt(statistics.mean(v * v for v in volatility)) if volatility else 0.0
    amplitude = clamp(pooled_vol, 0.35, 0.45)
    days = case['horizon_minutes'] / 1440.0
    stale = 0.35 if len(reads) < 2 else 0.0
    sigmas = []
    rows = []
    normal = statistics.NormalDist()
    zs = [normal.inv_cdf(level) for level in case['levels']]
    for trophy, median, last_rate in zip(case['trophies'], medians, last_rates):
        if last_rate is None:
            sigma = 2.0
        else:
            move = abs(logit(median) - logit(last_rate))
            sigma = max(0.05, math.sqrt(amplitude ** 2 * days +
                                       (0.5 * move) ** 2 + stale ** 2 * days))
        sigmas.append(sigma)
        quantiles = []
        for z in zs:
            value = round4(inv_logit(logit(median) + z * sigma))
            value = clamp(value, 0.0, 100.0)
            quantiles.append(max(quantiles[-1] if quantiles else 0.0, value))
        rows.append({'id': trophy['id'], 'q': quantiles})
    return {'trophies': rows}, sigmas, medians


def main():
    input_dir = Path(os.environ.get('MAKEFUN_INPUT_DIR', '/input'))
    output_dir = Path(os.environ.get('MAKEFUN_OUTPUT_DIR', '/output'))
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(input_dir.glob('*.in')):
        case = load_case(path)
        output, _, _ = forecast_details(case)
        payload = json.dumps(output, separators=(',', ':'), allow_nan=False) + '\n'
        (output_dir / (str(case['id']) + '.out')).write_text(payload, encoding='utf-8')


if __name__ == '__main__':
    main()
