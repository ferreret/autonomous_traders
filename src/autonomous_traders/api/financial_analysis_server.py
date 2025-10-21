import yfinance as yf
import pandas_ta as ta
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import List, Dict, Any

# --- Configuración del Servidor MCP ---
mcp = FastMCP("financial_analysis_server")

# --- Ayudante de Análisis de Sentimiento ---
POSITIVE_WORDS = ["up", "gain", "surpass", "beat", "strong", "rise", "bullish", "optimistic", "growth", "expand", "profit", "success", "upgrade"]
NEGATIVE_WORDS = ["down", "loss", "miss", "weak", "fall", "drop", "bearish", "pessimistic", "decline", "shrink", "slump", "downgrade", "risk"]

def simple_sentiment_analysis(text: str) -> int:
    """
    Realiza un análisis de sentimiento muy básico contando palabras clave positivas y negativas.
    Devuelve +1 para positivo, -1 para negativo, 0 para neutral.
    """
    score = 0
    text_lower = text.lower()
    for word in POSITIVE_WORDS:
        if word in text_lower:
            score += 1
    for word in NEGATIVE_WORDS:
        if word in text_lower:
            score -= 1
    
    if score > 0:
        return 1
    elif score < 0:
        return -1
    else:
        return 0

# --- Modelos Pydantic para Entradas de Herramientas ---
class SymbolInput(BaseModel):
    symbol: str = Field(description="El símbolo bursátil (p. ej., 'AAPL', 'TSLA').")

class TechnicalIndicatorsInput(BaseModel):
    symbol: str = Field(description="El símbolo bursátil.")
    indicators: List[str] = Field(description="Una lista de indicadores a calcular (p. ej., ['SMA_50', 'RSI_14']).")

# --- Implementaciones de Herramientas ---

@mcp.tool()
async def get_fundamental_data(args: SymbolInput) -> Dict[str, Any]:
    """
    Obtiene datos fundamentales clave para una empresa, como su relación P/E, capitalización de mercado y más.
    """
    try:
        ticker = yf.Ticker(args.symbol)
        info = ticker.info

        # Extraer una lista curada de puntos de datos fundamentales
        fundamental_data = {
            "market_cap": info.get("marketCap"),
            "forward_pe": info.get("forwardPE"),
            "trailing_pe": info.get("trailingPE"),
            "price_to_book": info.get("priceToBook"),
            "enterprise_to_revenue": info.get("enterpriseToRevenue"),
            "enterprise_to_ebitda": info.get("enterpriseToEbitda"),
            "profit_margins": info.get("profitMargins"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "dividend_yield": info.get("dividendYield"),
        }
        # Filtrar valores None
        return {k: v for k, v in fundamental_data.items() if v is not None}
    except Exception as e:
        return {"error": f"No se pudieron recuperar los datos fundamentales para {args.symbol}: {str(e)}"}

@mcp.tool()
async def get_technical_indicators(args: TechnicalIndicatorsInput) -> Dict[str, Any]:
    """
    Calcula uno o más indicadores técnicos para un símbolo de acción durante el último año.
    Ejemplos de indicadores: 'SMA_50' (Media Móvil Simple de 50 días), 'RSI_14' (Índice de Fuerza Relativa de 14 días), 'MACD_12_26_9'.
    """
    try:
        ticker = yf.Ticker(args.symbol)
        hist = ticker.history(period="1y")

        if hist.empty:
            return {"error": f"No se encontraron datos históricos para el símbolo {args.symbol}"}

        # Crear una estrategia personalizada para pandas-ta
        strategy = ta.Strategy(
            name="Custom Indicators",
            ta=[{"kind": indicator.lower()} for indicator in args.indicators]
        )
        
        # Aplicar la estrategia
        hist.ta.strategy(strategy)

        # Obtener el último valor para cada indicador solicitado
        latest_indicators = {}
        for indicator in args.indicators:
            # pandas-ta crea columnas con nombres como 'SMA_50', 'RSI_14', etc.
            # Necesitamos encontrar el nombre exacto de la columna, ya que puede tener variaciones (p. ej., MACD crea múltiples columnas)
            for col in hist.columns:
                if indicator.upper() in col.upper():
                     # Obtener el último valor no NaN
                    last_value = hist[col].dropna().iloc[-1]
                    latest_indicators[col] = float(last_value)

        return latest_indicators
    except Exception as e:
        return {"error": f"No se pudieron calcular los indicadores técnicos para {args.symbol}: {str(e)}"}

@mcp.tool()
async def get_news_sentiment(args: SymbolInput) -> Dict[str, Any]:
    """
    Analiza los titulares de noticias más recientes para un símbolo y devuelve un sentimiento general.
    """
    try:
        ticker = yf.Ticker(args.symbol)
        news = ticker.news

        if not news:
            return {"symbol": args.symbol, "sentiment": "Neutral", "reason": "No se encontraron noticias recientes."}

        total_score = 0
        headlines = []
        for item in news:
            headline = item.get("title", "")
            headlines.append(headline)
            total_score += simple_sentiment_analysis(headline)
        
        if total_score > 0:
            sentiment = "Positive"
        elif total_score < 0:
            sentiment = "Negative"
        else:
            sentiment = "Neutral"

        return {
            "symbol": args.symbol,
            "sentiment": sentiment,
            "overall_score": total_score,
            "analyzed_headlines": len(headlines)
        }
    except Exception as e:
        return {"error": f"No se pudo recuperar el sentimiento de las noticias para {args.symbol}: {str(e)}"}


if __name__ == "__main__":
    mcp.run(transport="stdio")
