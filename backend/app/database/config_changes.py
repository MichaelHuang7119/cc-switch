"""Config changes database operations."""
import json
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class ConfigChangesManager:
    """Manages configuration changes in the database."""

    def __init__(self, db_core):
        """
        Initialize config changes manager.

        Args:
            db_core: DatabaseCore instance for connection management.
        """
        self.db_core = db_core

    async def log_config_change(
        self,
        change_type: str,
        entity_type: str,
        entity_name: str,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        changed_by: Optional[str] = None
    ):
        """Log a configuration change."""
        conn = None
        cursor = None
        try:
            conn = await self.db_core.get_connection()
            cursor = await conn.cursor()

            await cursor.execute("""
                INSERT INTO config_changes (
                    change_type, entity_type, entity_name, old_value, new_value, changed_by
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                change_type,
                entity_type,
                entity_name,
                json.dumps(old_value, ensure_ascii=False) if old_value else None,
                json.dumps(new_value, ensure_ascii=False) if new_value else None,
                changed_by
            ))

            await conn.commit()
        except Exception as e:
            logger.error(f"Failed to log config change: {e}")
        finally:
            if cursor is not None:
                try:
                    await cursor.close()
                except Exception:
                    pass
            if conn is not None:
                await self.db_core.release_connection(conn)

    async def get_config_changes(
        self,
        limit: int = 100,
        entity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get configuration changes."""
        conn = None
        cursor = None
        try:
            conn = await self.db_core.get_connection()
            cursor = await conn.cursor()

            query = "SELECT * FROM config_changes"
            params = []

            if entity_type:
                query += " WHERE entity_type = ?"
                params.append(entity_type)

            query += " ORDER BY changed_at DESC LIMIT ?"
            params.append(limit)

            await cursor.execute(query, params)
            rows = await cursor.fetchall()

            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get config changes: {e}")
            return []
        finally:
            if cursor is not None:
                try:
                    await cursor.close()
                except Exception:
                    pass
            if conn is not None:
                await self.db_core.release_connection(conn)
