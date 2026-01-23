"""API Key management database operations."""
import aiosqlite
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class APIKeysManager:
    """Manages API keys in the database."""

    def __init__(self, db_core):
        """
        Initialize API keys manager.

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
        """Execute a query and return results with proper resource cleanup.

        Args:
            query: SQL query to execute
            params: Query parameters
            fetch_one: If True, return single row
            fetch_all: If True, return all rows

        Returns:
            Query results based on fetch mode
        """
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
        """Execute an update/insert query with proper resource cleanup.

        Args:
            query: SQL query to execute
            params: Query parameters
            commit: Whether to commit the transaction

        Returns:
            Number of rows affected or last row id
        """
        cursor = None
        conn = None
        try:
            conn = await self.db_core.get_connection()
            cursor = await conn.cursor()
            await cursor.execute(query, params or ())

            if commit:
                await conn.commit()

            return cursor.lastrowid if query.strip().upper().startswith("INSERT") else cursor.rowcount
        except Exception as e:
            if query.strip().upper().startswith("INSERT"):
                logger.error(f"Failed to create API key: {e}")
            elif "UPDATE" in query.upper():
                logger.error(f"Failed to update API key: {e}")
            elif "DELETE" in query.upper():
                logger.error(f"Failed to delete API key: {e}")
            else:
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

    async def create_api_key(
        self,
        key_hash: str,
        key_prefix: str,
        name: str,
        encrypted_key: Optional[str] = None,
        email: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Optional[int]:
        """Create a new API key.

        Returns:
            API key ID if successful, None if key already exists.
        """
        try:
            api_key_id = await self._execute_update(
                """
                INSERT INTO api_keys (key_hash, key_prefix, encrypted_key, name, email, user_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (key_hash, key_prefix, encrypted_key, name, email, user_id)
            )
            logger.info(f"Created API key: {name}")
            return api_key_id
        except aiosqlite.IntegrityError:
            logger.error("API key already exists")
            return None

    async def get_api_key_by_hash(self, key_hash: str) -> Optional[Dict[str, Any]]:
        """Get API key by hash.

        Returns:
            API key info dict if found and active, None otherwise.
        """
        row = await self._execute_query(
            """
            SELECT id, key_hash, key_prefix, encrypted_key, name, email, user_id, is_active, created_at, last_used_at, updated_at
            FROM api_keys WHERE key_hash = ? AND is_active = 1
            """,
            (key_hash,),
            fetch_one=True
        )
        return dict(row) if row else None

    async def get_api_keys(
        self,
        user_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
        name_filter: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """Get API keys with optional filters.

        Returns:
            List of API key info dicts.
        """
        query = "SELECT * FROM api_keys WHERE 1=1"
        params = []

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        if name_filter:
            query += " AND name LIKE ?"
            params.append(f"%{name_filter}%")

        if is_active is not None:
            query += " AND is_active = ?"
            params.append(1 if is_active else 0)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = await self._execute_query(query, tuple(params), fetch_all=True)
        return [dict(row) for row in rows] if rows else []

    async def get_api_keys_count(
        self,
        user_id: Optional[int] = None,
        name_filter: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> int:
        """Get total count of API keys matching filters.

        Returns:
            Count of matching API keys.
        """
        query = "SELECT COUNT(*) as count FROM api_keys WHERE 1=1"
        params = []

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        if name_filter:
            query += " AND name LIKE ?"
            params.append(f"%{name_filter}%")

        if is_active is not None:
            query += " AND is_active = ?"
            params.append(1 if is_active else 0)

        row = await self._execute_query(query, tuple(params), fetch_one=True)
        return row["count"] if row else 0

    async def update_api_key(
        self,
        api_key_id: int,
        name: Optional[str] = None,
        email: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> bool:
        """Update API key.

        Returns:
            True if update was successful, False otherwise.
        """
        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if email is not None:
            updates.append("email = ?")
            params.append(email)
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(is_active)

        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(api_key_id)

        query = f"UPDATE api_keys SET {', '.join(updates)} WHERE id = ?"
        row_count = await self._execute_update(query, tuple(params))
        return row_count > 0

    async def delete_api_key(self, api_key_id: int) -> bool:
        """Delete API key.

        Returns:
            True if deletion was successful, False otherwise.
        """
        row_count = await self._execute_update(
            "DELETE FROM api_keys WHERE id = ?",
            (api_key_id,)
        )
        return row_count > 0

    async def update_api_key_last_used(self, api_key_id: int) -> None:
        """Update API key's last used time."""
        await self._execute_update(
            """
            UPDATE api_keys SET last_used_at = CURRENT_TIMESTAMP WHERE id = ?
            """,
            (api_key_id,),
            commit=True
        )

    async def get_api_key_encrypted(self, api_key_id: int) -> Optional[Dict[str, Any]]:
        """Get API key info including encrypted full key by ID.

        Returns:
            API key info dict if found, None otherwise.
        """
        row = await self._execute_query(
            "SELECT * FROM api_keys WHERE id = ?",
            (api_key_id,),
            fetch_one=True
        )
        return dict(row) if row else None
