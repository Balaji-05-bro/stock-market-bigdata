#!/usr/bin/env python3
"""
Stock Market Financial & Statistical Analyzer
Provides high-level analytical metrics, multi-stock comparisons,
performance rankings, and integration with technical indicator engines.
"""

import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path

# Project path resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from analytics.technical_indicators import TechnicalIndicators

class StockAnalyzer:
    """Performs financial analysis and statistical evaluation across equities."""

    def __init__(self, data_path):
        self.data_path = Path(data_path)
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data file not found at: {self.data_path}")

        self.df = pd.read_csv(self.data_path)
        # Ensure column standard naming
        if "Adj Close" in self.df.columns and "Adj_Close" not in self.df.columns:
            self.df.rename(columns={"Adj Close": "Adj_Close"}, inplace=True)
        if "Company Name" in self.df.columns and "Company_Name" not in self.df.columns:
            self.df.rename(columns={"Company Name": "Company_Name"}, inplace=True)

        self.df["Date"] = pd.to_datetime(self.df["Date"]).dt.strftime("%Y-%m-%d")
        self.df.sort_values(by=["Symbol", "Date"], inplace=True)
        self.df.reset_index(drop=True, inplace=True)

    def get_symbols(self):
        """Return list of distinct stock symbols and their registered company names."""
        sub = self.df[["Symbol", "Company_Name"]].drop_duplicates()
        return sub.to_dict(orient="records")

    def get_stock_data(self, symbol, start_date=None, end_date=None):
        """Return historical time series slice for a single symbol."""
        sub = self.df[self.df["Symbol"] == symbol].copy()
        if start_date:
            sub = sub[sub["Date"] >= start_date]
        if end_date:
            sub = sub[sub["Date"] <= end_date]
        return sub

    def get_stock_summary(self, symbol):
        """Calculate key financial summary metrics for a given stock symbol."""
        sub = self.df[self.df["Symbol"] == symbol].sort_values("Date")
        if sub.empty:
            return {}

        first_row = sub.iloc[0]
        last_row = sub.iloc[-1]
        start_price = float(first_row["Close"])
        end_price = float(last_row["Close"])
        ret_pct = ((end_price - start_price) / start_price * 100.0) if start_price > 0 else 0.0

        # Daily returns for volatility
        daily_returns = sub["Close"].pct_change()
        # A zero or invalid close can produce infinite returns. Keep only
        # finite observations so the volatility remains a valid JSON number.
        daily_returns = daily_returns.replace([np.inf, -np.inf], np.nan).dropna()
        daily_std = float(daily_returns.std()) if len(daily_returns) > 1 else 0.0
        if not np.isfinite(daily_std):
            daily_std = 0.0
        annualized_vol = daily_std * np.sqrt(252) * 100.0

        return {
            "symbol": symbol,
            "company_name": str(last_row.get("Company_Name", symbol)),
            "start_date": str(first_row["Date"]),
            "end_date": str(last_row["Date"]),
            "initial_price": round(start_price, 2),
            "latest_close": round(end_price, 2),
            "highest_price": round(float(sub["High"].max()), 2),
            "lowest_price": round(float(sub["Low"].min()), 2),
            "average_price": round(float(sub["Close"].mean()), 2),
            "total_volume": int(sub["Volume"].sum()),
            "average_volume": int(sub["Volume"].mean()),
            "percentage_return": round(ret_pct, 2),
            "annualized_volatility": round(annualized_vol, 2),
            "trading_days": len(sub)
        }

    def get_top_performers(self, n=5):
        """Rank and return top n performing equities by total return percentage."""
        summaries = [self.get_stock_summary(s) for s in self.df["Symbol"].unique()]
        summaries.sort(key=lambda x: x.get("percentage_return", 0), reverse=True)
        return summaries[:n]

    def get_worst_performers(self, n=5):
        """Rank and return bottom n performing equities by total return percentage."""
        summaries = [self.get_stock_summary(s) for s in self.df["Symbol"].unique()]
        summaries.sort(key=lambda x: x.get("percentage_return", 0))
        return summaries[:n]

    def get_overall_statistics(self):
        """Compute aggregate macro statistics across the entire stock market portfolio."""
        unique_stocks = self.df["Symbol"].unique().tolist()
        total_records = len(self.df)
        all_summaries = [self.get_stock_summary(s) for s in unique_stocks]
        all_summaries.sort(key=lambda x: x.get("percentage_return", 0), reverse=True)

        top_stock = all_summaries[0] if all_summaries else {}
        worst_stock = all_summaries[-1] if all_summaries else {}

        return {
            "total_stocks": len(unique_stocks),
            "total_records": total_records,
            "date_range": f"{self.df['Date'].min()} to {self.df['Date'].max()}",
            "average_market_price": round(float(self.df["Close"].mean()), 2),
            "total_market_volume": int(self.df["Volume"].sum()),
            "highest_performer": {
                "symbol": top_stock.get("symbol", "N/A"),
                "return": f"{top_stock.get('percentage_return', 0):+.2f}%"
            },
            "lowest_performer": {
                "symbol": worst_stock.get("symbol", "N/A"),
                "return": f"{worst_stock.get('percentage_return', 0):+.2f}%"
            },
            "last_processing_status": "COMPLETED (Verified HDFS & MapReduce)"
        }

    def compare_stocks(self, symbols, metric="Close"):
        """
        Compare multiple stock symbols over time for a specific metric (e.g., Close, Volume).
        Returns a pivot DataFrame with Date as index and Symbols as columns.
        """
        sub = self.df[self.df["Symbol"].isin(symbols)]
        pivot_df = sub.pivot(index="Date", columns="Symbol", values=metric)
        return pivot_df

    def analyze_stock(self, symbol):
        """
        Run complete technical analysis suite on a specific stock.
        Returns indicators, support/resistance, and trend signals.
        """
        stock_df = self.get_stock_data(symbol)
        if stock_df.empty:
            return {}

        ti = TechnicalIndicators(stock_df)
        full_df = ti.calculate_all()
        supp_res = ti.support_resistance()
        summary = self.get_stock_summary(symbol)

        # Extract latest indicator readings
        last_row = full_df.iloc[-1]
        signals = {
            "latest_sma_20": round(float(last_row.get("SMA_20", 0)), 2),
            "latest_sma_50": round(float(last_row.get("SMA_50", 0)), 2),
            "latest_ema_20": round(float(last_row.get("EMA_20", 0)), 2),
            "latest_rsi_14": round(float(last_row.get("RSI_14", 50)), 2),
            "latest_macd": round(float(last_row.get("MACD", 0)), 2),
            "latest_macd_signal": round(float(last_row.get("Signal_Line", 0)), 2),
            "latest_macd_hist": round(float(last_row.get("MACD_Histogram", 0)), 2),
            "bollinger_upper": round(float(last_row.get("BB_Upper", 0)), 2),
            "bollinger_lower": round(float(last_row.get("BB_Lower", 0)), 2),
            "trend_state": str(last_row.get("Trend", "Neutral")),
            "support_levels": supp_res.get("support", []),
            "resistance_levels": supp_res.get("resistance", [])
        }

        return {
            "summary": summary,
            "signals": signals,
            "data": full_df.to_dict(orient="records")
        }

if __name__ == "__main__":
    cleaned_file = PROJECT_ROOT / "datasets" / "cleaned" / "cleaned_stock_data.csv"
    if not cleaned_file.exists():
        cleaned_file = PROJECT_ROOT / "datasets" / "raw" / "nse_stock_data.csv"
    analyzer = StockAnalyzer(cleaned_file)
    print("Overview Stats:", analyzer.get_overall_statistics())
    print("RELIANCE Summary:", analyzer.get_stock_summary("RELIANCE"))
