"""Request logs database operations."""

import json
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class RequestLogsManager:
    """Manages request logs in the database."""

    def __init__(self, db_core):
        """
        Initialize request logs manager.

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

    async def log_request(
        self,
        request_id: str,
        provider_name: str,
        model: str,
        request_params: Dict[str, Any],
        response_data: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        response_time_ms: Optional[float] = None,
    ) -> None:
        """Log a request to the database."""
        await self._execute_update(
            """
            INSERT INTO request_logs (
                request_id, provider_name, model, request_params, response_data,
                status_code, error_message, input_tokens, output_tokens, response_time_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                provider_name,
                model,
                json.dumps(request_params, ensure_ascii=False),
                json.dumps(response_data, ensure_ascii=False) if response_data else None,
                status_code,
                error_message,
                input_tokens,
                output_tokens,
                response_time_ms,
            )
        )

    async def get_request_logs(
        self,
        limit: Optional[int] = 100,
        offset: int = 0,
        provider_name: Optional[str] = None,
        model: Optional[str] = None,
        status_code: Optional[int] = None,
        status_min: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get request logs with optional filters.

        Returns:
            List of request log dicts.
        """
        query = "SELECT * FROM request_logs WHERE 1=1"
        params = []

        if provider_name:
            query += " AND provider_name = ?"
            params.append(provider_name)

        if model:
            query += " AND model = ?"
            params.append(model)

        if status_code is not None:
            query += " AND status_code = ?"
            params.append(status_code)
        elif status_min is not None:
            query += " AND status_code >= ?"
            params.append(status_min)

        if date_from:
            query += " AND date(created_at) >= ?"
            params.append(date_from)

        if date_to:
            query += " AND date(created_at) <= ?"
            params.append(date_to)

        if limit is not None:
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        else:
            query += " ORDER BY created_at DESC"

        rows = await self._execute_query(query, tuple(params), fetch_all=True)
        return [dict(row) for row in rows] if rows else []

    async def get_request_logs_count(
        self,
        provider_name: Optional[str] = None,
        model: Optional[str] = None,
        status_code: Optional[int] = None,
        status_min: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> int:
        """Get total count of request logs with filters.

        Returns:
            Count of matching records.
        """
        query = "SELECT COUNT(*) FROM request_logs WHERE 1=1"
        params = []

        if provider_name:
            query += " AND provider_name = ?"
            params.append(provider_name)

        if model:
            query += " AND model = ?"
            params.append(model)

        if status_code is not None:
            query += " AND status_code = ?"
            params.append(status_code)
        elif status_min is not None:
            query += " AND status_code >= ?"
            params.append(status_min)

        if date_from:
            query += " AND date(created_at) >= ?"
            params.append(date_from)

        if date_to:
            query += " AND date(created_at) <= ?"
            params.append(date_to)

        result = await self._execute_query(query, tuple(params), fetch_one=True)
        return result[0] if result else 0
