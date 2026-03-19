import io
import os

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend; must be set before importing pyplot
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import yfinance as yf

CHARTS_DIR = os.path.join(os.path.dirname(__file__), "charts")

# Supported durations: user-facing value → (yfinance period, display label, intraday flag)
DURATION_CONFIG: dict[str, tuple[str, str, bool]] = {
    "1d":  ("1d",  "1-Day",    True),
    "5d":  ("5d",  "5-Day",    True),
    "1mo": ("1mo", "1-Month",  False),
    "3mo": ("3mo", "3-Month",  False),
    "1y":  ("1y",  "1-Year",   False),
}

VALID_DURATIONS = list(DURATION_CONFIG.keys())


def generate_stock_chart(symbol: str, duration: str = "1y") -> bytes:
    """Fetch stock data from yfinance and generate a PNG image that contains a
    candlestick chart and a table of the last 10 data points for the requested
    duration.

    Args:
        symbol: The stock ticker symbol (e.g. "AAPL").
        duration: One of ``"1d"``, ``"5d"``, ``"1mo"``, ``"3mo"``, ``"1y"``.
            Defaults to ``"1y"``.

    Returns:
        The raw PNG image as bytes. The image is also saved to the
        ``charts/`` directory next to this file.

    Raises:
        ValueError: If no data is found for the given symbol, or if the
            duration is not one of the supported values.
    """
    if duration not in DURATION_CONFIG:
        raise ValueError(
            f"Invalid duration '{duration}'. Valid options: {', '.join(VALID_DURATIONS)}"
        )

    period, duration_label, is_intraday = DURATION_CONFIG[duration]

    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=period)

    if hist.empty:
        raise ValueError(f"No data found for symbol '{symbol}'")

    info = ticker.info
    company_name = info.get("longName", symbol.upper())

    fig = plt.figure(figsize=(14, 10))
    gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1], hspace=0.5)

    # --- Candlestick chart ---
    ax_chart = fig.add_subplot(gs[0])

    # Compute the price range upfront so the doji fallback is scale-independent
    price_min = float(hist["Low"].min())
    price_max = float(hist["High"].max())
    price_range = price_max - price_min if price_max != price_min else price_max

    n = len(hist)

    for i, (_, row) in enumerate(hist.iterrows()):
        open_p = row["Open"]
        high_p = row["High"]
        low_p  = row["Low"]
        close_p = row["Close"]
        color = "#26a69a" if close_p >= open_p else "#ef5350"  # green up, red down

        # Wick: thin vertical line spanning the full High–Low range
        ax_chart.plot([i, i], [low_p, high_p], color=color, linewidth=1, zorder=1)

        # Body: rectangle from Open to Close
        body_bottom = min(open_p, close_p)
        body_height = abs(close_p - open_p)
        # Doji candle (Open == Close): give a minimal visible height that is
        # independent of the stock price (0.1% of the full price range).
        if body_height == 0:
            body_height = price_range * 0.001
        rect = mpatches.Rectangle(
            (i - 0.4, body_bottom),
            0.8,
            body_height,
            facecolor=color,
            edgecolor=color,
            linewidth=0.5,
            zorder=2,
        )
        ax_chart.add_patch(rect)

    ax_chart.set_xlim(-1, n)

    # X-axis tick labels: show a manageable number of date/time labels
    max_ticks = 10
    step = max(1, n // max_ticks)
    tick_positions = list(range(0, n, step))
    if is_intraday:
        tick_labels = [hist.index[i].strftime("%Y-%m-%d %H:%M") for i in tick_positions]
    else:
        tick_labels = [hist.index[i].strftime("%Y-%m-%d") for i in tick_positions]
    ax_chart.set_xticks(tick_positions)
    ax_chart.set_xticklabels(tick_labels, rotation=45, ha="right")

    ax_chart.set_title(
        f"{company_name} ({symbol.upper()}) – {duration_label} Price",
        fontsize=14,
        fontweight="bold",
        pad=10,
    )
    ax_chart.set_xlabel("Time" if is_intraday else "Date")
    ax_chart.set_ylabel("Price (USD)")
    ax_chart.grid(True, alpha=0.3)

    # Legend patches
    ax_chart.legend(
        handles=[
            mpatches.Patch(color="#26a69a", label="Bullish (Close ≥ Open)"),
            mpatches.Patch(color="#ef5350", label="Bearish (Close < Open)"),
        ]
    )

    # Set y-axis limits to the actual High/Low range with a 5% buffer based on
    # the lowest price so wicks are never clipped.
    # Example: lowest=100, highest=200 → buffer=5 → y-axis 95–205.
    buffer = price_min * 0.05
    ax_chart.set_ylim(price_min - buffer, price_max + buffer)

    # --- Recent data table (last 10 data points) ---
    ax_table = fig.add_subplot(gs[1])
    ax_table.axis("off")
    ax_table.set_title("Recent Trading Data (Last 10 Entries)", fontsize=11, pad=5)

    recent = hist.tail(10).copy()
    if is_intraday:
        recent.index = recent.index.strftime("%Y-%m-%d %H:%M")
        time_col_label = "Time"
    else:
        recent.index = recent.index.strftime("%Y-%m-%d")
        time_col_label = "Date"
    table_data = recent[["Open", "High", "Low", "Close", "Volume"]].round(2)
    table_data["Volume"] = table_data["Volume"].apply(lambda x: f"{int(x):,}")

    col_labels = [time_col_label, "Open", "High", "Low", "Close", "Volume"]
    rows = [[idx] + list(row) for idx, row in zip(table_data.index, table_data.values.tolist())]

    table = ax_table.table(
        cellText=rows,
        colLabels=col_labels,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.5)

    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#0066CC")
            cell.set_text_props(color="white", fontweight="bold")
        elif row % 2 == 0:
            cell.set_facecolor("#f0f0f0")

    # Save to a BytesIO buffer, then persist to disk from the same bytes
    os.makedirs(CHARTS_DIR, exist_ok=True)
    file_path = os.path.join(CHARTS_DIR, f"{symbol.upper()}_{duration}.png")

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    image_bytes = buf.read()

    with open(file_path, "wb") as f:
        f.write(image_bytes)

    return image_bytes
