"""Database management for user authorization and usage tracking."""
import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict
import config


class Database:
    """Manages SQLite database for user data and usage statistics."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DATABASE_PATH
        self.init_database()

    def get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)

    def init_database(self):
        """Initialize database tables."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_authorized INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Usage statistics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                model TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                cost_usd REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        # Conversation history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT,
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        conn.commit()

        # Ensure admin user exists
        if config.ADMIN_USER_ID:
            cursor.execute("""
                INSERT OR REPLACE INTO users (user_id, is_authorized, is_admin)
                VALUES (?, 1, 1)
            """, (config.ADMIN_USER_ID,))
            conn.commit()

        conn.close()

    def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT is_authorized FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result and result[0] == 1

    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result and result[0] == 1

    def add_user(self, user_id: int, username: str = None, first_name: str = None,
                 last_name: str = None, is_authorized: bool = False):
        """Add or update user information."""
        conn = self.get_connection()
        cursor = conn.cursor()
        # Use INSERT ... ON CONFLICT to preserve is_admin when updating
        cursor.execute("""
            INSERT INTO users (user_id, username, first_name, last_name, is_authorized, last_active)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                last_active = CURRENT_TIMESTAMP
        """, (user_id, username, first_name, last_name, int(is_authorized)))
        conn.commit()
        conn.close()

    def authorize_user(self, user_id: int):
        """Authorize a user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_authorized = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

    def deauthorize_user(self, user_id: int):
        """Deauthorize a user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_authorized = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

    def get_all_users(self) -> List[Dict]:
        """Get all users."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, username, first_name, last_name, is_authorized, is_admin, created_at
            FROM users ORDER BY created_at DESC
        """)
        users = []
        for row in cursor.fetchall():
            users.append({
                "user_id": row[0],
                "username": row[1],
                "first_name": row[2],
                "last_name": row[3],
                "is_authorized": bool(row[4]),
                "is_admin": bool(row[5]),
                "created_at": row[6]
            })
        conn.close()
        return users

    def log_usage(self, user_id: int, model: str, input_tokens: int, output_tokens: int):
        """Log API usage and calculate cost."""
        pricing = config.CLAUDE_PRICING.get(model, {"input": 3.00, "output": 15.00})
        cost = (input_tokens / 1_000_000 * pricing["input"] +
                output_tokens / 1_000_000 * pricing["output"])

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO usage_stats (user_id, model, input_tokens, output_tokens, cost_usd)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, model, input_tokens, output_tokens, cost))
        conn.commit()
        conn.close()

        return cost

    def get_total_usage(self) -> Dict:
        """Get total usage statistics."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                SUM(input_tokens) as total_input,
                SUM(output_tokens) as total_output,
                SUM(cost_usd) as total_cost,
                COUNT(*) as total_requests
            FROM usage_stats
        """)
        row = cursor.fetchone()
        conn.close()

        return {
            "total_input_tokens": row[0] or 0,
            "total_output_tokens": row[1] or 0,
            "total_cost": row[2] or 0.0,
            "total_requests": row[3] or 0
        }

    def get_user_usage(self, user_id: int) -> Dict:
        """Get usage statistics for a specific user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                SUM(input_tokens) as total_input,
                SUM(output_tokens) as total_output,
                SUM(cost_usd) as total_cost,
                COUNT(*) as total_requests
            FROM usage_stats
            WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        conn.close()

        return {
            "total_input_tokens": row[0] or 0,
            "total_output_tokens": row[1] or 0,
            "total_cost": row[2] or 0.0,
            "total_requests": row[3] or 0
        }

    def add_message_to_history(self, user_id: int, role: str, content: str):
        """Add message to conversation history."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO conversations (user_id, role, content)
            VALUES (?, ?, ?)
        """, (user_id, role, content))
        conn.commit()
        conn.close()

    def get_conversation_history(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Get recent conversation history for a user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT role, content, timestamp
            FROM conversations
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (user_id, limit))

        messages = []
        for row in reversed(cursor.fetchall()):  # Reverse to get chronological order
            messages.append({
                "role": row[0],
                "content": row[1]
            })
        conn.close()
        return messages

    def clear_conversation_history(self, user_id: int):
        """Clear conversation history for a user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
