import os

from dotenv import load_dotenv
from autonomous_traders.core.market import is_paid_polygon, is_realtime_polygon

load_dotenv(override=True)

brave_env = {"BRAVE_API_KEY": os.getenv("BRAVE_API_KEY")}
polygon_api_key = os.getenv("POLYGON_API_KEY")

# El servidor MCP para que el Trader lea datos de mercado

if is_paid_polygon or is_realtime_polygon:
    market_mcp = {
        "command": "uvx",
        "args": [
            "--from",
            "git+https://github.com/polygon-io/mcp_polygon@master",
            "mcp_polygon",
        ],
        "env": {"POLYGON_API_KEY": polygon_api_key},
    }
else:
    market_mcp = {"command": "uv", "args": ["run", "-m", "autonomous_traders.api.market_server"]}


# El conjunto completo de servidores MCP para el trader: Cuentas (solo propuestas), Notificaciones Push, Análisis Financiero y Mercado
trader_mcp_server_params = [
    {"command": "uv", "args": ["run", "-m", "autonomous_traders.api.accounts_server"]}, # Ahora solo para proponer operaciones
    {"command": "uv", "args": ["run", "-m", "autonomous_traders.api.push_server"]},
    {"command": "uv", "args": ["run", "-m", "autonomous_traders.api.financial_analysis_server"]},
    market_mcp,
]

# El conjunto completo de servidores MCP para el investigador: Fetch, Brave Search y Memoria

def researcher_mcp_server_params(name: str):
    return [
        {"command": "uvx", "args": ["mcp-server-fetch"]},
        {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "env": brave_env,
        },
        {
            "command": "npx",
            "args": ["-y", "mcp-memory-libsql"],
            "env": {"LIBSQL_URL": f"file:./memory/{name}.db"},
        },
    ]

# El conjunto completo de servidores MCP para el supervisor: Cuentas (lectura), Mercado (precios), Ejecución y Base de Datos
supervisor_mcp_server_params = [
    {"command": "uv", "args": ["run", "-m", "autonomous_traders.api.accounts_server"]}, # Para leer cuentas y estrategias
    market_mcp, # Para obtener precios de acciones
    {"command": "uv", "args": ["run", "-m", "autonomous_traders.api.execution_server"]}, # Para ejecutar operaciones aprobadas
    {"command": "uv", "args": ["run", "-m", "autonomous_traders.api.database_server"]}, # Para gestionar operaciones pendientes y logs
]