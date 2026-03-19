from typing import Literal

from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from stock_chart import generate_stock_chart

app = FastAPI(title="TradeStamp API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Welcome to TradeStamp API"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get(
    "/stock/{symbol}/chart",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}, "description": "Stock chart PNG image"}},
)
def get_stock_chart(
    symbol: str = Path(..., description="Stock ticker symbol (e.g. AAPL, MSFT, TSLA)"),
    duration: Literal["1d", "5d", "1mo", "3mo", "1y"] = Query(
        default="1y",
        description="Duration of the chart data. One of: 1d (1 day), 5d (5 days), "
                    "1mo (1 month), 3mo (3 months), 1y (1 year).",
    ),
):
    """Return a PNG chart for the requested stock symbol and duration.

    The chart contains a closing-price graph and a table of the last
    10 data points for the selected duration. The generated file is also
    saved to ``backend/charts/``.
    """
    try:
        image_bytes = generate_stock_chart(symbol, duration)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Failed to fetch stock data: {exc}") from exc

    return Response(content=image_bytes, media_type="image/png")
