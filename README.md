# GTA VI Trophy Rarity Forecast

![gta6-trophy-rarity-forecast-01](https://make.fun/badge/gta6-trophy-rarity-forecast-01.svg)
![rank](https://make.fun/badge/gta6-trophy-rarity-forecast-01/jembot21/gta6-trophy-rarity-forecast/rank.svg)
![reward](https://make.fun/badge/gta6-trophy-rarity-forecast-01/jembot21/gta6-trophy-rarity-forecast/reward.svg)

This repository is my entry to the [make.fun GTA VI trophy rarity forecast bounty](https://make.fun/bounty/gta6-trophy-rarity-forecast-01). make.fun is a platform for forecasting contests and bounties.

The model estimates trophy earner counts separately from growth in the tracked-player pool, then converts the predicted counts into rarity rates. It fits trends in log-time and shrinks sparse trophy trends toward the pooled trend. Forecast uncertainty uses observed logit-scale volatility, the expected forecast move, and a wider spread when there is only one distinct read.

Run it with case files in the input directory and forecasts in the output directory:

```sh
MAKEFUN_INPUT_DIR=/path/to/input MAKEFUN_OUTPUT_DIR=/path/to/output python3 main.py
```

Both environment variables are optional; they default to `/input` and `/output`.
