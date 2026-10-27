"""População do banco de dados SQLite (database.db) com usuários e predições.

Este módulo atende ao requisito explícito do TP3 de disponibilizar o arquivo
`fastapi/sqlite_populate.py` para popular o banco de dados.

Uso:
    python sqlite_populate.py
"""
import os
import sqlite3
import bcrypt

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")

USERS = [
    ("admin", "admin123"),
    ("alice", "alice123"),
]

# (dono, texto, intenção, confiança)
PREDICTIONS = [
    ("admin", "Quero meu dinheiro de volta, o produto veio com defeito", "Refund Request", 0.91),
    ("admin", "Meu produto parou de funcionar", "Technical Issue", 0.87),
    ("alice", "Preciso cancelar meu pedido", "Cancellation Request", 0.88),
    ("alice", "Tenho uma dúvida sobre a fatura deste mês", "Billing Inquiry", 0.85),
]


def hash_password(password: str) -> str:
    """Gera hash seguro com bcrypt e salt aleatório."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def populate_database(path: str = DB_PATH) -> None:
    """Popula o banco SQLite existente com usuários e predições de teste."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Banco {path} não encontrado. Execute sqlite_database.py primeiro para criar o schema."
        )

    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")

        # Inserção de usuários (evita duplicatas se já existirem)
        for username, password in USERS:
            conn.execute(
                "INSERT OR IGNORE INTO user (username, hashed_password) VALUES (?, ?)",
                (username, hash_password(password)),
            )

        ids = {name: uid for uid, name in conn.execute("SELECT id, username FROM user")}

        # Limpa e reinsere predições para garantir determinismo
        conn.execute("DELETE FROM prediction")
        for owner, text, intent, confidence in PREDICTIONS:
            if owner in ids:
                conn.execute(
                    "INSERT INTO prediction (owner_id, text, intent, confidence) VALUES (?, ?, ?, ?)",
                    (ids[owner], text, intent, confidence),
                )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    populate_database()
    print(f"Banco populado com sucesso em {DB_PATH}")
