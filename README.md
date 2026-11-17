# GTA VI Twitch CCU Forecast Entry

[![make.fun](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/sybl2710-creator/gta6-twitch-ccu-forecast-01/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/sybl2710-creator/gta6-twitch-ccu-forecast-01/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01)

This entry provides probabilistic hourly concurrent viewer (CCU) forecasts for the launch day of Grand Theft Auto VI on Twitch, leveraging historical comparable game launches and pre-release momentum features.

## How it works

- **Comparable Launch Modeling:** Filters and analyzes historical launch day curves from comparable game releases on Twitch.
- **Per-Hour OLS Regression:** Fits an Ordinary Least Squares regression model for each launch hour (hours 2 through 24) predicting viewer ratios relative to hour 1, incorporating baseline viewer scale (`p1`), non-linear scale terms, and pre-release momentum growth features (`g`).
- **Probabilistic Quantiles:** Computes median forecasts and generates prediction intervals across standard quantile levels (0.05, 0.25, 0.50, 0.75, 0.95) using residual standard deviation.

Runs on Python 3.13 standard library only.
