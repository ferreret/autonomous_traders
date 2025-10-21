import asyncio
import os
import json
from contextlib import AsyncExitStack

from agents import add_trace_processor
from agents.mcp import MCPServerStdio

from autonomous_traders.core.supervisor import Supervisor
from autonomous_traders.utils.tracers import LogTracer

# Importar funciones de cliente para los servidores MCP
from autonomous_traders.utils.accounts_client import read_account_resource, read_strategy_resource

# Importar los parámetros de los servidores MCP
from autonomous_traders.utils.mcp_params import (
    market_mcp,
    researcher_mcp_server_params # Aunque no se usa directamente aquí, es bueno tenerlo en cuenta
)

# --- Constantes de Configuración ---
RUN_SUPERVISOR_EVERY_N_SECONDS = int(os.getenv("RUN_SUPERVISOR_EVERY_N_SECONDS", "30"))

# --- Parámetros de los Servidores MCP para el Supervisor ---
# El supervisor necesita acceso a:
# - accounts_server: para leer el estado de la cuenta y la estrategia del trader
# - market_server: para obtener el precio actual de las acciones (para cálculo de riesgo)
# - execution_server: para ejecutar las operaciones aprobadas
# - database_server: para obtener operaciones pendientes, actualizar su estado y escribir logs

supervisor_mcp_server_params = [
    {"command": "uv", "args": ["run", "-m", "autonomous_traders.api.accounts_server"]},
    market_mcp, # Reutilizamos la configuración del mercado
    {"command": "uv", "args": ["run", "-m", "autonomous_traders.api.execution_server"]},
    {"command": "uv", "args": ["run", "-m", "autonomous_traders.api.database_server"]},
]

async def run_supervisor_periodically():
    add_trace_processor(LogTracer())
    supervisor = Supervisor() # El modelo se inicializa dentro de la clase

    print(f"Iniciando el Supervisor para ejecutarse cada {RUN_SUPERVISOR_EVERY_N_SECONDS} segundos...")

    while True:
        async with AsyncExitStack() as stack:
            # Iniciar los servidores MCP necesarios para el supervisor
            supervisor_servers = [
                await stack.enter_async_context(
                    MCPServerStdio(params, client_session_timeout_seconds=120) # type: ignore
                )
                for params in supervisor_mcp_server_params
            ]
            supervisor.agent.mcp_servers = supervisor_servers

            try:
                # Obtener operaciones pendientes del database_server
                pending_trades_response = await supervisor.agent.call_tool("get_all_pending_trades", {})
                pending_trades = pending_trades_response.get("result", [])

                if pending_trades:
                    print(f"Supervisor: Revisando {len(pending_trades)} operaciones pendientes.")
                    for trade in pending_trades:
                        trade_id = trade["id"]
                        trader_name = trade["trader_name"]
                        symbol = trade["symbol"]
                        quantity = trade["quantity"]
                        rationale = trade["rationale"]

                        # Obtener datos adicionales para la decisión del supervisor
                        trader_account_report = await read_account_resource(trader_name)
                        trader_account = json.loads(trader_account_report)
                        trader_strategy = await read_strategy_resource(trader_name)
                        
                        # Obtener el precio actual de la acción para el cálculo de riesgo
                        market_price_response = await supervisor.agent.call_tool("lookup_share_price", {"symbol": symbol})
                        market_price = market_price_response.get("result", 0.0)

                        # Tomar la decisión
                        decision_output = await supervisor.decide_on_trade(
                            trade_proposal=trade,
                            trader_account=trader_account,
                            trader_strategy=trader_strategy,
                            market_price=market_price
                        )
                        decision = decision_output.get("decision", "REJECT")
                        feedback = decision_output.get("feedback", "No se proporcionó feedback.")

                        print(f"Supervisor: Operación {trade_id} ({symbol}, {quantity}) de {trader_name} - Decisión: {decision}")

                        # Registrar la decisión del supervisor
                        await supervisor.agent.call_tool(
                            "write_agent_log",
                            {"name": trader_name, "type": "supervisor", "message": f"Supervisor: {decision} - {feedback}"}
                        )

                        if decision == "APPROVE":
                            # Ejecutar la operación a través del execution_server
                            if quantity > 0:
                                execution_response = await supervisor.agent.call_tool(
                                    "execute_buy_shares",
                                    {
                                        "trader_name": trader_name,
                                        "symbol": symbol,
                                        "quantity": quantity,
                                        "rationale": rationale
                                    }
                                )
                            else:
                                execution_response = await supervisor.agent.call_tool(
                                    "execute_sell_shares",
                                    {
                                        "trader_name": trader_name,
                                        "symbol": symbol,
                                        "quantity": abs(quantity),
                                        "rationale": rationale
                                    }
                                )
                            print(f"Supervisor: Ejecución de {trade_id}: {execution_response}")
                            # Actualizar estado en la base de datos
                            await supervisor.agent.call_tool(
                                "update_pending_trade_status",
                                {"trade_id": trade_id, "status": "approved", "supervisor_feedback": feedback}
                            )
                        else: # REJECT
                            # Actualizar estado en la base de datos
                            await supervisor.agent.call_tool(
                                "update_pending_trade_status",
                                {"trade_id": trade_id, "status": "rejected", "supervisor_feedback": feedback}
                            )
                else:
                    print("Supervisor: No hay operaciones pendientes para revisar.")

            except Exception as e:
                print(f"Error en el bucle del Supervisor: {e}")

        await asyncio.sleep(RUN_SUPERVISOR_EVERY_N_SECONDS)


if __name__ == "__main__":
    asyncio.run(run_supervisor_periodically())
