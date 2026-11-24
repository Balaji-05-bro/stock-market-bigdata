"""
Technical Indicators Module
============================

Provides a comprehensive suite of technical analysis indicators for stock
market data. All calculations use standard, well-documented formulas from
quantitative finance.

DISCLAIMER
----------
The indicators computed by this module are for **educational and informational
purposes only**. They do **NOT** constitute investment advice, trading signals,
or recommendations to buy, sell, or hold any financial instrument. Past
performance is not indicative of future results. Always consult a qualified
financial advisor before making investment decisions.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class TechnicalIndicators:
    """Calculate common technical indicators on OHLCV stock data.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with columns:
        ``Date``, ``Symbol``, ``Open``, ``High``, ``Low``, ``Close``,
        ``Adj_Close``, ``Volume``.

    Raises
    ------
    ValueError
        If any required column is missing from *df*.
    TypeError
        If *df* is not a ``pandas.DataFrame``.
    """

    _REQUIRED_COLUMNS = {"Date", "Symbol", "Open", "High", "Low",
                         "Close", "Adj_Close", "Volume"}

    def __init__(self, df: pd.DataFrame) -> None:
        if not isinstance(df, pd.DataFrame):
            raise TypeError(
                f"Expected a pandas DataFrame, got {type(df).__name__}."
            )

        missing = self._REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(
                f"DataFrame is missing required columns: {missing}"
            )

        self.df = df.copy()

        # Ensure Date is datetime and the frame is sorted chronologically.
        self.df["Date"] = pd.to_datetime(self.df["Date"])
        self.df.sort_values("Date", inplace=True)
        self.df.reset_index(drop=True, inplace=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_period(self, period: int, name: str = "period") -> None:
        """Raise ``ValueError`` if *period* is not a positive integer."""
        if not isinstance(period, int) or period < 1:
            raise ValueError(f"`{name}` must be a positive integer, got {period}.")

    def _validate_column(self, column: str) -> None:
        """Raise ``ValueError`` if *column* is not in the DataFrame."""
        if column not in self.df.columns:
            raise ValueError(
                f"Column '{column}' not found. "
                f"Available columns: {list(self.df.columns)}"
            )

    # ------------------------------------------------------------------
    # Indicators
    # ------------------------------------------------------------------

    def sma(self, period: int = 20, column: str = "Close") -> pd.Series:
        """Simple Moving Average (SMA).

        Formula
        -------
        SMA_t = (1 / n) * Σ_{i=0}^{n-1} P_{t-i}

        where *n* = ``period`` and *P* is the price series given by
        ``column``.

        Parameters
        ----------
        period : int, default 20
            Look-back window in trading days.
        column : str, default ``'Close'``
            Column to compute the average on.

        Returns
        -------
        pd.Series
            The SMA values, indexed identically to ``self.df``.

        Note
        ----
        This is a lagging indicator. It does **not** predict future prices.
        """
        self._validate_period(period)
        self._validate_column(column)

        sma_series = self.df[column].rolling(window=period, min_periods=period).mean()
        sma_series.name = f"SMA_{period}"
        return sma_series

    def ema(self, period: int = 20, column: str = "Close") -> pd.Series:
        """Exponential Moving Average (EMA).

        Formula
        -------
        EMA_t = α · P_t + (1 − α) · EMA_{t−1}

        where α = 2 / (n + 1) and *n* = ``period``.

        Parameters
        ----------
        period : int, default 20
            Span of the EMA.
        column : str, default ``'Close'``
            Column to compute the average on.

        Returns
        -------
        pd.Series
            The EMA values.

        Note
        ----
        The EMA reacts more quickly to recent price changes than the SMA.
        It is **not** a prediction of future prices.
        """
        self._validate_period(period)
        self._validate_column(column)

        ema_series = self.df[column].ewm(span=period, adjust=False).mean()
        ema_series.name = f"EMA_{period}"
        return ema_series

    def daily_returns(self, column: str = "Close") -> pd.Series:
        """Daily percentage returns.

        Formula
        -------
        R_t = (P_t − P_{t−1}) / P_{t−1}  =  P_t / P_{t−1} − 1

        Parameters
        ----------
        column : str, default ``'Close'``
            Price column to compute returns on.

        Returns
        -------
        pd.Series
            Fractional daily returns (multiply by 100 for percent).
            The first value is ``NaN``.

        Note
        ----
        Historical returns do **not** guarantee future performance.
        """
        self._validate_column(column)

        returns = self.df[column].pct_change()
        returns.name = "Daily_Return"
        return returns

    def macd(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> pd.DataFrame:
        """Moving Average Convergence Divergence (MACD).

        Formula
        -------
        MACD_line   = EMA(Close, fast) − EMA(Close, slow)
        Signal_line = EMA(MACD_line, signal)
        Histogram   = MACD_line − Signal_line

        Default parameters (12, 26, 9) are the classic Gerald Appel values.

        Parameters
        ----------
        fast : int, default 12
            Fast EMA period.
        slow : int, default 26
            Slow EMA period.
        signal : int, default 9
            Signal line EMA period.

        Returns
        -------
        pd.DataFrame
            Columns: ``MACD``, ``Signal``, ``Histogram``.

        Note
        ----
        MACD is a momentum / trend-following indicator. Cross-overs are
        commonly cited heuristics but are **not** reliable stand-alone
        trading signals.
        """
        self._validate_period(fast, "fast")
        self._validate_period(slow, "slow")
        self._validate_period(signal, "signal")

        if fast >= slow:
            raise ValueError(
                f"`fast` period ({fast}) must be less than `slow` ({slow})."
            )

        ema_fast = self.df["Close"].ewm(span=fast, adjust=False).mean()
        ema_slow = self.df["Close"].ewm(span=slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return pd.DataFrame({
            "MACD": macd_line,
            "Signal": signal_line,
            "Histogram": histogram,
        })

    def rsi(self, period: int = 14) -> pd.Series:
        """Relative Strength Index (RSI) using Wilder's smoothing method.

        Formula
        -------
        1.  Δ_t  = Close_t − Close_{t−1}
        2.  Gain = max(Δ_t, 0),  Loss = max(−Δ_t, 0)
        3.  First average gain/loss = SMA of first *n* gains/losses.
        4.  Subsequent:
                AvgGain_t = (AvgGain_{t−1} · (n − 1) + Gain_t) / n
                AvgLoss_t = (AvgLoss_{t−1} · (n − 1) + Loss_t) / n
        5.  RS  = AvgGain / AvgLoss
        6.  RSI = 100 − 100 / (1 + RS)

        Common thresholds
        -----------------
        * RSI > 70  → conventionally considered "overbought"
        * RSI < 30  → conventionally considered "oversold"

        These thresholds are **heuristics**, not guaranteed reversal points.

        Parameters
        ----------
        period : int, default 14
            Look-back window (Wilder originally used 14).

        Returns
        -------
        pd.Series
            RSI values in [0, 100].

        Note
        ----
        RSI is a momentum oscillator. It is **not** a trading signal.
        """
        self._validate_period(period)

        delta = self.df["Close"].diff()
        gain = delta.clip(lower=0.0)
        loss = (-delta).clip(lower=0.0)

        # Wilder's smoothing (equivalent to EMA with alpha = 1/period)
        avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

        rs = avg_gain / avg_loss
        rsi_series = 100.0 - (100.0 / (1.0 + rs))
        rsi_series.name = f"RSI_{period}"
        return rsi_series

    def bollinger_bands(
        self,
        period: int = 20,
        std_dev: float = 2.0,
    ) -> pd.DataFrame:
        """Bollinger Bands®.

        Formula
        -------
        Middle = SMA(Close, n)
        Upper  = Middle + k · σ_n
        Lower  = Middle − k · σ_n

        where *n* = ``period``, *k* = ``std_dev``, and σ_n is the rolling
        standard deviation of Close over the last *n* periods.

        Parameters
        ----------
        period : int, default 20
            SMA / standard-deviation window.
        std_dev : float, default 2.0
            Number of standard deviations for the upper/lower bands.

        Returns
        -------
        pd.DataFrame
            Columns: ``BB_Upper``, ``BB_Middle``, ``BB_Lower``.

        Note
        ----
        Bollinger Bands measure volatility; they do **not** predict
        direction.
        """
        self._validate_period(period)
        if std_dev <= 0:
            raise ValueError(f"`std_dev` must be positive, got {std_dev}.")

        middle = self.df["Close"].rolling(window=period, min_periods=period).mean()
        rolling_std = self.df["Close"].rolling(window=period, min_periods=period).std()

        upper = middle + std_dev * rolling_std
        lower = middle - std_dev * rolling_std

        return pd.DataFrame({
            "BB_Upper": upper,
            "BB_Middle": middle,
            "BB_Lower": lower,
        })

    def historical_volatility(self, period: int = 30) -> pd.Series:
        """Annualised historical (realised) volatility.

        Formula
        -------
        1.  log_return_t = ln(Close_t / Close_{t−1})
        2.  σ_period     = std(log_return over last *period* days)
        3.  Annualised   = σ_period × √252

        252 is the conventional number of trading days in a year.

        Parameters
        ----------
        period : int, default 30
            Rolling window (trading days) for the standard deviation.

        Returns
        -------
        pd.Series
            Annualised volatility (as a decimal; multiply by 100 for %).

        Note
        ----
        Historical volatility looks backward. It does **not** forecast
        future volatility.
        """
        self._validate_period(period)

        log_returns = np.log(self.df["Close"] / self.df["Close"].shift(1))
        vol = log_returns.rolling(window=period, min_periods=period).std() * np.sqrt(252)
        vol.name = f"HV_{period}"
        return vol

    def identify_trends(
        self,
        short_period: int = 20,
        long_period: int = 50,
    ) -> pd.DataFrame:
        """Identify trend direction using dual-SMA crossover.

        Rules (heuristic, **not** trading advice)
        ------------------------------------------
        * **Bullish** : short SMA > long SMA.
        * **Bearish** : short SMA < long SMA.
        * **Neutral** : either SMA is NaN (insufficient data).
        * **Golden Cross** : short SMA crosses *above* long SMA.
        * **Death Cross**  : short SMA crosses *below* long SMA.

        Parameters
        ----------
        short_period : int, default 20
            Period of the faster SMA.
        long_period : int, default 50
            Period of the slower SMA.

        Returns
        -------
        pd.DataFrame
            Columns: ``SMA_Short``, ``SMA_Long``, ``Trend``,
            ``Golden_Cross``, ``Death_Cross``.

        Note
        ----
        Trend identification is a simplified heuristic. It is **not** a
        reliable predictor of future price movement.
        """
        self._validate_period(short_period, "short_period")
        self._validate_period(long_period, "long_period")
        if short_period >= long_period:
            raise ValueError(
                f"`short_period` ({short_period}) must be less than "
                f"`long_period` ({long_period})."
            )

        sma_short = self.sma(period=short_period)
        sma_long = self.sma(period=long_period)

        trend = pd.Series("Neutral", index=self.df.index, name="Trend")
        valid = sma_short.notna() & sma_long.notna()
        trend[valid & (sma_short > sma_long)] = "Bullish"
        trend[valid & (sma_short < sma_long)] = "Bearish"

        # Crossover signals
        prev_short = sma_short.shift(1)
        prev_long = sma_long.shift(1)
        golden_cross = valid & (sma_short > sma_long) & (prev_short <= prev_long)
        death_cross = valid & (sma_short < sma_long) & (prev_short >= prev_long)

        return pd.DataFrame({
            "SMA_Short": sma_short,
            "SMA_Long": sma_long,
            "Trend": trend,
            "Golden_Cross": golden_cross,
            "Death_Cross": death_cross,
        })

    def support_resistance(self, window: int = 20) -> dict:
        """Identify approximate support and resistance levels.

        Method
        ------
        * **Support levels** – local minima of ``Low`` within a rolling
          window of ``2 * window + 1`` bars centred on each bar.
        * **Resistance levels** – local maxima of ``High`` within the same
          centred window.

        A point is a local extremum if it equals the rolling min (or max)
        over the centred window.

        Parameters
        ----------
        window : int, default 20
            Half-width of the centred window used to detect local extrema.

        Returns
        -------
        dict
            ``{"support": list[float], "resistance": list[float]}``
            Each list contains unique price levels rounded to two decimals,
            sorted ascending.

        Note
        ----
        Support and resistance are **retrospective** observations.  They
        may or may not hold in the future.
        """
        self._validate_period(window, "window")

        full_window = 2 * window + 1

        # Local minima of Low → support
        rolling_min = self.df["Low"].rolling(
            window=full_window, center=True, min_periods=1
        ).min()
        support_mask = self.df["Low"] == rolling_min
        support_levels = sorted(self.df.loc[support_mask, "Low"].round(2).unique().tolist())

        # Local maxima of High → resistance
        rolling_max = self.df["High"].rolling(
            window=full_window, center=True, min_periods=1
        ).max()
        resistance_mask = self.df["High"] == rolling_max
        resistance_levels = sorted(self.df.loc[resistance_mask, "High"].round(2).unique().tolist())

        return {
            "support": support_levels,
            "resistance": resistance_levels,
        }

    def calculate_all(self) -> pd.DataFrame:
        """Calculate all indicators and return a merged DataFrame.

        The returned DataFrame contains every column of the original data
        plus the following computed columns:

        * ``SMA_20``, ``EMA_20``
        * ``Daily_Return``
        * ``MACD``, ``Signal``, ``Histogram``
        * ``RSI_14``
        * ``BB_Upper``, ``BB_Middle``, ``BB_Lower``
        * ``HV_30``
        * ``SMA_Short``, ``SMA_Long``, ``Trend``, ``Golden_Cross``,
          ``Death_Cross``

        Returns
        -------
        pd.DataFrame
            Original data augmented with all computed indicator columns.

        Note
        ----
        All indicators are descriptive statistics derived from historical
        data.  They are **not** trading signals or financial advice.
        """
        result = self.df.copy()

        result["SMA_20"] = self.sma(period=20)
        result["SMA_50"] = self.sma(period=50)
        result["EMA_20"] = self.ema(period=20)
        result["Daily_Return"] = self.daily_returns()

        macd_df = self.macd()
        result["MACD"] = macd_df["MACD"]
        result["Signal"] = macd_df["Signal"]
        result["Histogram"] = macd_df["Histogram"]

        result["RSI_14"] = self.rsi(period=14)

        bb_df = self.bollinger_bands()
        result["BB_Upper"] = bb_df["BB_Upper"]
        result["BB_Middle"] = bb_df["BB_Middle"]
        result["BB_Lower"] = bb_df["BB_Lower"]

        result["HV_30"] = self.historical_volatility(period=30)

        trend_df = self.identify_trends()
        result["SMA_Short"] = trend_df["SMA_Short"]
        result["SMA_Long"] = trend_df["SMA_Long"]
        result["Trend"] = trend_df["Trend"]
        result["Golden_Cross"] = trend_df["Golden_Cross"]
        result["Death_Cross"] = trend_df["Death_Cross"]

        return result
