from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="量化交易平台 API",
    description="量化交易单均线策略分析平台",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "量化交易平台 API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "quant-trading-platform"}

@app.get("/api/v1/market-data/symbols")
async def get_symbols():
    return {
        "symbols": [
            {"symbol": "CU2401", "name": "沪铜2401", "exchange": "SHFE"},
            {"symbol": "AL2401", "name": "沪铝2401", "exchange": "SHFE"},
            {"symbol": "ZN2401", "name": "沪锌2401", "exchange": "SHFE"}
        ]
    }

@app.post("/api/v1/strategies/run")
async def run_strategy(params: dict):
    return {
        "success": True,
        "strategy_id": f"strategy_test_{params.get('symbol', 'unknown')}",
        "results": {
            "total_return": 0.1245,
            "max_drawdown": -0.0823,
            "sharpe_ratio": 1.23,
            "signal_data": [
                {"date": "2024-01-01", "close": 68500, "ma": 68200, "signal": 1},
                {"date": "2024-01-02", "close": 68800, "ma": 68300, "signal": 1}
            ]
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)