import io
import os

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend; must be set before importing pyplot
import matplotlib.gridspec as gridspec
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
    closing-price chart and a table of the last 10 data points for the
    requested duration.

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

    # --- Price history chart ---
    ax_chart = fig.add_subplot(gs[0])
    ax_chart.plot(hist.index, hist["Close"], color="#0066CC", linewidth=1.5, label="Close Price")
    ax_chart.fill_between(hist.index, hist["Close"], alpha=0.1, color="#0066CC")
    ax_chart.set_title(
        f"{company_name} ({symbol.upper()}) – {duration_label} Closing Price",
        fontsize=14,
        fontweight="bold",
        pad=10,
    )
    ax_chart.set_xlabel("Time" if is_intraday else "Date")
    ax_chart.set_ylabel("Price (USD)")
    ax_chart.legend()
    ax_chart.grid(True, alpha=0.3)
    ax_chart.tick_params(axis="x", rotation=45)

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
