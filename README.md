# gta6-twitch-ccu-forecast-01

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/shieui/gta6-twitch-ccu-forecast-01/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/shieui/gta6-twitch-ccu-forecast-01/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

Forecasts how many people watch Grand Theft Auto VI live on Twitch in each hour of its release day, 2026-11-19 (UTC), after the first hour.

Entry for the [make.fun](https://make.fun/bounty/gta6-twitch-ccu-forecast-01) competition `gta6-twitch-ccu-forecast-01`.

## Run it

```sh
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

`main.py` (Python 3.13, standard library only) reads one case file at `$MAKEFUN_INPUT_DIR` (else `/input/`) and writes `$MAKEFUN_OUTPUT_DIR` (else `/output/`) `<id>.out`: for each of hours 2 to 24, five quantiles (0.05, 0.25, 0.5, 0.75, 0.95) of that hour's concurrent viewer count.

## Method

Launch-day shape from comparable past launches, conditioned on the size of hour 1. For each comparable launch, form the log-ratio of each hour's viewers to that launch's hour-1 viewers, and for each hour regress that log-ratio on the log of the launch's hour-1 viewers. A bigger hour 1 means a flatter launch day, so a small launch is forecast a steep rise and a huge launch a nearly flat day. Only clean comparables with a real launch hour 1 are used. The median is the regression prediction at the target's hour-1 size, clamped to the comparables' range; the spread is the per-hour residual spread, smoothed over neighbouring hours.

## Practice

Scored on the four practice cases (past big game launches) the model reaches a mean pinball loss of 0.178 on the log scale, against 0.387 for the house baseline (typical miss 30.1% vs 82.7%, 90% coverage 0.935 vs 0.783).

## License

MIT — see `LICENSE`.

---

<sub>Entered on [make.fun](https://make.fun/?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>
