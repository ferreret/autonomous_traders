import json
import sqlite3
from datetime import datetime

from dotenv import load_dotenv

load_dotenv(override=True)

DB = "accounts.db"


def get_db_connection():
    """Crea una conexión a la base de datos con el modo WAL activado."""
    conn = sqlite3.connect(DB, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# Creación de la tabla inicial
with get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS accounts (name TEXT PRIMARY KEY, account TEXT)"
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            datetime DATETIME,
            type TEXT,
            message TEXT
        )
    """
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS market (date TEXT PRIMARY KEY, data TEXT)"
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pending_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trader_name TEXT NOT NULL,
            symbol TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            rationale TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            supervisor_feedback TEXT
        )
    """
    )
    conn.commit()


def write_account(name, account_dict):
    json_data = json.dumps(account_dict)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO accounts (name, account)
            VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET account=excluded.account
        """,
            (name.lower(), json_data),
        )
        conn.commit()


def read_account(name):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT account FROM accounts WHERE name = ?", (name.lower(),))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None


def write_log(name: str, type: str, message: str):
    now = datetime.now().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO logs (name, datetime, type, message)
            VALUES (?, datetime('now'), ?, ?)
        """,
            (name.lower(), type, message),
        )
        conn.commit()


def read_log(name: str, last_n=10):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT datetime, type, message FROM logs 
            WHERE name = ? 
            ORDER BY datetime DESC
            LIMIT ?
        """,
            (name.lower(), last_n),
        )
        return reversed(cursor.fetchall())


def write_market(date: str, data: dict) -> None:
    data_json = json.dumps(data)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO market (date, data)
            VALUES (?, ?)
            ON CONFLICT(date) DO UPDATE SET data=excluded.data
        """,
            (date, data_json),
        )
        conn.commit()


def read_market(date: str) -> dict | None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM market WHERE date = ?", (date,))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None

# --- Funciones para Operaciones Pendientes ---

def create_pending_trade(trader_name: str, symbol: str, quantity: int, rationale: str):
    """Crea un registro para una nueva propuesta de operación en estado pendiente."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO pending_trades (trader_name, symbol, quantity, rationale)
            VALUES (?, ?, ?, ?)
            """,
            (trader_name.lower(), symbol, quantity, rationale),
        )
        conn.commit()
        return cursor.lastrowid

def get_pending_trades() -> list[dict]:
    """Obtiene todas las operaciones que están actualmente en estado pendiente."""
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row  # Devuelve filas que se comportan como diccionarios
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pending_trades WHERE status = 'pending'")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def update_trade_status(trade_id: int, status: str, supervisor_feedback: str | None = None):
    """Actualiza el estado de una operación pendiente (p. ej., a 'approved' o 'rejected')."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE pending_trades
            SET status = ?, supervisor_feedback = ?
            WHERE id = ?
            """,
            (status, supervisor_feedback, trade_id),
        )
        conn.commit()
