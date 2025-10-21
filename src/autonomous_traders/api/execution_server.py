from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from autonomous_traders.core.accounts import Account

mcp = FastMCP("execution_server")

# --- Modelos Pydantic para Entradas de Herramientas ---

class ExecuteTradeInput(BaseModel):
    trader_name: str = Field(description="El nombre del trader cuya cuenta se utilizará para la operación.")
    symbol: str = Field(description="El símbolo bursátil de la operación.")
    quantity: int = Field(description="La cantidad de acciones a operar.")
    rationale: str = Field(description="La justificación original de la operación para el registro de la transacción.")

# --- Implementaciones de Herramientas ---

@mcp.tool()
async def execute_buy_shares(args: ExecuteTradeInput) -> str:
    """
    EJECUCIÓN FINAL: Compra acciones para la cuenta de un trader.
    Esta herramienta solo debe ser utilizada por un supervisor para ejecutar una operación aprobada.
    """
    try:
        account = Account.get(args.trader_name)
        result = account.buy_shares(
            symbol=args.symbol,
            quantity=args.quantity,
            rationale=f"(Aprobado por el Supervisor) {args.rationale}"
        )
        return f"COMPRA EJECUTADA para {args.trader_name}: {args.quantity} de {args.symbol}. Resultado: {result}"
    except Exception as e:
        return f"ERROR DE EJECUCIÓN de compra para {args.trader_name}: {str(e)}"

@mcp.tool()
async def execute_sell_shares(args: ExecuteTradeInput) -> str:
    """
    EJECUCIÓN FINAL: Vende acciones de la cuenta de un trader.
    Esta herramienta solo debe ser utilizada por un supervisor para ejecutar una operación aprobada.
    """
    try:
        account = Account.get(args.trader_name)
        result = account.sell_shares(
            symbol=args.symbol,
            quantity=args.quantity,
            rationale=f"(Aprobado por el Supervisor) {args.rationale}"
        )
        return f"VENTA EJECUTADA para {args.trader_name}: {args.quantity} de {args.symbol}. Resultado: {result}"
    except Exception as e:
        return f"ERROR DE EJECUCIÓN de venta para {args.trader_name}: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
