# GTA VI Trophy Rarity Forecast

A deterministic Python 3 standard-library forecaster for trophy earn-rate quantiles. It collapses consecutive duplicate reads, maps elapsed release hours onto a logarithmic time axis, and fits player counts and trophy earner counts by ordinary least squares. Trophy slopes shrink toward a pooled mean; sparse trophies use pooled median growth. Bounded earner estimates yield median rates, while pooled daily logit volatility, horizon, trend displacement, missing data and staleness determine uncertainty. Normal quantiles in logit space become bounded, half-up rounded percentage forecasts.

[![Bounty](https://make.fun/badge/gta6-trophy-rarity-forecast-01.svg)](https://make.fun/competitions/gta6-trophy-rarity-forecast-01)
[![Rank](https://make.fun/badge/gta6-trophy-rarity-forecast-01/jembot21/gta6-trophy-rarity-forecast/rank.svg)](https://make.fun/competitions/gta6-trophy-rarity-forecast-01)
[![Reward](https://make.fun/badge/gta6-trophy-rarity-forecast-01/jembot21/gta6-trophy-rarity-forecast/reward.svg)](https://make.fun/competitions/gta6-trophy-rarity-forecast-01)

Run `python3 main.py`. Set `MAKEFUN_INPUT_DIR` and `MAKEFUN_OUTPUT_DIR` to override `/input` and `/output`. Inputs are processed in filename order; each case produces compact JSON in `<id>.out`, with rows sorted by trophy ID.

Repository: built for the make.fun bounty `gta6-trophy-rarity-forecast-01`. Publishing this repository does not submit an entry to make.fun.
