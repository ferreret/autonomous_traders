import json
import sqlite3
from datetime import datetime

from dotenv import load_dotenv

load_dotenv(override=True)

DB = "accounts.db"


def get_db_connection():
    """Crea una conexión a la base de datos con el modo WAL activado."""
    # Se ha aumentado el tiempo de espera y se ha activado el modo WAL para evitar los errores "database is locked" (la base de datos está bloqueada)
    # durante las lecturas simultáneas de la aplicación Gradio y las escrituras de los traders.
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
    """
    Escribe una entrada de registro en la tabla de registros.

    Args:
        name (str): El nombre asociado con el registro
        type (str): El tipo de entrada de registro
        message (str): El mensaje de registro
    """
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
    """
    Lee las entradas de registro más recientes para un nombre determinado.

    Args:
        name (str): El nombre para el que se recuperarán los registros
        last_n (int): El número de entradas más recientes que se van a recuperar

    Returns:
        list: Una lista de tuplas que contienen (datetime, type, message)
    """
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