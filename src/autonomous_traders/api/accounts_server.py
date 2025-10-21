from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from autonomous_traders.core.accounts import Account
from autonomous_traders.data.database import create_pending_trade

mcp = FastMCP("accounts_server")

# --- Modelos Pydantic para Entradas de Herramientas ---

class ProposeTradeInput(BaseModel):
    trader_name: str = Field(description="El nombre del trader que realiza la propuesta.")
    symbol: str = Field(description="El símbolo bursátil de la operación (p. ej., 'AAPL', 'TSLA').")
    quantity: int = Field(description="La cantidad de acciones a operar. Usa un número positivo para comprar y un número negativo para vender.")
    rationale: str = Field(description="Una justificación detallada de por qué se realiza esta operación, vinculándola a tu estrategia de inversión.")

# --- Implementaciones de Herramientas ---

@mcp.tool()
async def propose_trade(args: ProposeTradeInput) -> str:
    """
    Propone una operación de compra o venta para que sea revisada por un supervisor.
    No ejecuta la operación directamente.
    """
    try:
        trade_id = create_pending_trade(
            trader_name=args.trader_name,
            symbol=args.symbol,
            quantity=args.quantity,
            rationale=args.rationale
        )
        return f"Operación propuesta con éxito. ID de la propuesta: {trade_id}. Esperando la revisión del supervisor."
    except Exception as e:
        return f"Error al proponer la operación: {str(e)}"

@mcp.tool()
async def get_balance(name: str) -> float:
    """Obtiene el saldo en efectivo de la cuenta indicada."""
    return Account.get(name).balance

@mcp.tool()
async def get_holdings(name: str) -> dict[str, int]:
    """Obtiene las tenencias de la cuenta indicada."""
    return Account.get(name).holdings

@mcp.tool()
async def change_strategy(name: str, strategy: str) -> str:
    """A tu discreción, si lo deseas, llama a esto para cambiar tu estrategia de inversión futura."""
    return Account.get(name).change_strategy(strategy)


@mcp.resource("accounts://accounts_server/{name}")
async def read_account_resource(name: str) -> str:
    account = Account.get(name.lower())
    return account.report()


@mcp.resource("accounts://strategy/{name}")
async def read_strategy_resource(name: str) -> str:
    account = Account.get(name.lower())
    return account.get_strategy()


if __name__ == "__main__":
    mcp.run(transport="stdio")