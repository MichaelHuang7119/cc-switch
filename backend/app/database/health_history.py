"""Health history database operations."""
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class HealthHistoryManager:
    """Manages provider health history in the database."""

    def __init__(self, db_core):
        """
        Initialize health history manager.

        Args:
            db_core: DatabaseCore instance for connection management.
        """
        self.db_core = db_core

    async def log_health_status(
        self,
        provider_name: str,
        status: str,
        response_time_ms: Optional[float] = None,
        error_message: Optional[str] = None
    ):
        """Log provider health status."""
        conn = None
        cursor = None
        try:
            conn = await self.db_core.get_connection()
            cursor = await conn.cursor()

            await cursor.execute("""
                INSERT INTO provider_health_history (
                    provider_name, status, response_time_ms, error_message
                ) VALUES (?, ?, ?, ?)
            """, (provider_name, status, response_time_ms, error_message))

            await conn.commit()
        except Exception as e:
            logger.error(f"Failed to log health status: {e}")
        finally:
            if cursor is not None:
                try:
                    await cursor.close()
                except Exception:
                    pass
            if conn is not None:
                await self.db_core.release_connection(conn)

    async def get_health_history(
        self,
        provider_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get provider health history."""
        conn = None
        cursor = None
        try:
            conn = await self.db_core.get_connection()
            cursor = await conn.cursor()

            query = "SELECT * FROM provider_health_history"
            params = []

            if provider_name:
                query += " WHERE provider_name = ?"
                params.append(provider_name)

            query += " ORDER BY checked_at DESC LIMIT ?"
            params.append(limit)

            await cursor.execute(query, params)
            rows = await cursor.fetchall()

            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get health history: {e}")
            return []
        finally:
            if cursor is not None:
                try:
                    await cursor.close()
                except Exception:
                    pass
            if conn is not None:
                await self.db_core.release_connection(conn)
