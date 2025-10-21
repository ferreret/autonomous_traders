from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import List, Dict, Any

from autonomous_traders.data.database import get_pending_trades, update_trade_status, write_log

mcp = FastMCP("database_server")

# --- Pydantic Models for Tool Inputs ---

class UpdateTradeStatusInput(BaseModel):
    trade_id: int = Field(description="El ID de la operación pendiente a actualizar.")
    status: str = Field(description="El nuevo estado de la operación (p. ej., 'approved', 'rejected').")
    supervisor_feedback: str | None = Field(default=None, description="Feedback del supervisor sobre la decisión.")

class LogInput(BaseModel):
    name: str = Field(description="El nombre asociado con el registro (p. ej., el nombre del trader o 'Supervisor').")
    type: str = Field(description="El tipo de entrada de registro (p. ej., 'supervisor', 'decision', 'feedback').")
    message: str = Field(description="El mensaje de registro.")

# --- Tool Implementations ---

@mcp.tool()
async def get_all_pending_trades() -> List[Dict[str, Any]]:
    """
    Obtiene una lista de todas las operaciones que están actualmente en estado pendiente.
    """
    try:
        return get_pending_trades()
    except Exception as e:
        return {"error": f"Error al obtener operaciones pendientes: {str(e)}"}

@mcp.tool()
async def update_pending_trade_status(args: UpdateTradeStatusInput) -> str:
    """
    Actualiza el estado de una operación pendiente y añade feedback del supervisor.
    """
    try:
        update_trade_status(args.trade_id, args.status, args.supervisor_feedback)
        return f"Estado de la operación {args.trade_id} actualizado a {args.status}."
    except Exception as e:
        return {"error": f"Error al actualizar el estado de la operación {args.trade_id}: {str(e)}"}

@mcp.tool()
async def write_agent_log(args: LogInput) -> str:
    """
    Escribe una entrada de registro para un agente específico o para el supervisor.
    """
    try:
        write_log(args.name, args.type, args.message)
        return "Registro escrito con éxito."
    except Exception as e:
        return {"error": f"Error al escribir el registro: {str(e)}"}


if __name__ == "__main__":
    mcp.run(transport="stdio")
