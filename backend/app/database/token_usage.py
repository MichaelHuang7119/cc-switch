"""Token usage database operations."""
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class TokenUsageManager:
    """Manages token usage statistics in the database."""

    def __init__(self, db_core):
        """
        Initialize token usage manager.

        Args:
            db_core: DatabaseCore instance for connection management.
        """
        self.db_core = db_core

    async def _execute_query(
        self,
        query: str,
        params: tuple = None,
        fetch_one: bool = False,
        fetch_all: bool = False
    ) -> Optional[Any]:
        """Execute a query with proper resource cleanup."""
        cursor = None
        conn = None
        try:
            conn = await self.db_core.get_connection()
            cursor = await conn.cursor()
            await cursor.execute(query, params or ())

            if fetch_one:
                return await cursor.fetchone()
            elif fetch_all:
                return await cursor.fetchall()
            return None
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            raise
        finally:
            if cursor is not None:
                try:
                    await cursor.close()
                except Exception:
                    pass
            if conn is not None:
                await self.db_core.release_connection(conn)

    async def _execute_update(
        self,
        query: str,
        params: tuple = None,
        commit: bool = True
    ) -> int:
        """Execute an update/insert/delete query with proper resource cleanup."""
        cursor = None
        conn = None
        try:
            conn = await self.db_core.get_connection()
            cursor = await conn.cursor()
            await cursor.execute(query, params or ())

            if commit:
                await conn.commit()

            query_upper = query.strip().upper()
            if query_upper.startswith("INSERT"):
                return cursor.lastrowid
            return cursor.rowcount
        except Exception as e:
            logger.error(f"Database update failed: {e}")
            raise
        finally:
            if cursor is not None:
                try:
                    await cursor.close()
                except Exception:
                    pass
            if conn is not None:
                await self.db_core.release_connection(conn)

    async def update_token_usage(
        self,
        date: str,
        provider_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_estimate: float
    ) -> None:
        """Update token usage statistics.

        Uses UPSERT pattern: try to update, insert if not exists.
        """
        # Try to update existing record
        row_count = await self._execute_update(
            """
            UPDATE token_usage
            SET request_count = request_count + 1,
                total_input_tokens = total_input_tokens + ?,
                total_output_tokens = total_output_tokens + ?,
                total_cost_estimate = total_cost_estimate + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE date = ? AND provider_name = ? AND model = ?
            """,
            (input_tokens, output_tokens, cost_estimate, date, provider_name, model)
        )

        # If no rows were updated (row_count == 0), insert new record
        if row_count == 0:
            await self._execute_update(
                """
                INSERT INTO token_usage (
                    date, provider_name, model, request_count,
                    total_input_tokens, total_output_tokens, total_cost_estimate
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (date, provider_name, model, 1, input_tokens, output_tokens, cost_estimate)
            )

    async def get_token_usage_summary(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get token usage summary.

        Returns:
            Summary dict with usage statistics.
        """
        query = "SELECT * FROM token_usage WHERE 1=1"
        params = []

        if date_from:
            query += " AND date >= ?"
            params.append(date_from)

        if date_to:
            query += " AND date <= ?"
            params.append(date_to)

        query += " ORDER BY date DESC"

        rows = await self._execute_query(query, tuple(params), fetch_all=True)

        if not rows:
            return {
                "summary": [],
                "total_requests": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cost_estimate": 0
            }

        return {
            "summary": [dict(row) for row in rows],
            "total_requests": sum(row["request_count"] for row in rows),
            "total_input_tokens": sum(row["total_input_tokens"] for row in rows),
            "total_output_tokens": sum(row["total_output_tokens"] for row in rows),
            "total_cost_estimate": sum(row["total_cost_estimate"] for row in rows)
        }
