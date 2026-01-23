"""User management database operations."""
import aiosqlite
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class UsersManager:
    """Manages users in the database."""

    def __init__(self, db_core):
        """
        Initialize users manager.

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
        """Execute a query with proper resource cleanup.

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
        """Execute an update/insert/delete query with proper resource cleanup.

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

            query_upper = query.strip().upper()
            if query_upper.startswith("INSERT"):
                return cursor.lastrowid
            elif query_upper.startswith("UPDATE") or query_upper.startswith("DELETE"):
                return cursor.rowcount
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

    async def create_user(
        self,
        email: str,
        password_hash: Optional[str] = None,
        name: Optional[str] = None,
        is_admin: bool = True
    ) -> Optional[int]:
        """
        Create a new user with default permissions based on role.

        Args:
            email: User email
            password_hash: Hashed password (can be None for OAuth2 users)
            name: User name
            is_admin: Is admin user

        Returns:
            User ID if successful, None if user already exists.
        """
        try:
            # For OAuth2 users, password can be None
            if password_hash is None:
                password_hash = ""  # Empty string for OAuth2 users

            # Initialize permissions based on role (use lowercase keys for frontend compatibility)
            from ..core.permissions import DEFAULT_USER_PERMISSIONS, ADMIN_PERMISSIONS
            if is_admin:
                permissions = {k.value.lower(): v for k, v in ADMIN_PERMISSIONS.items()}
            else:
                permissions = {k.value.lower(): v for k, v in DEFAULT_USER_PERMISSIONS.items()}

            user_id = await self._execute_update(
                """
                INSERT INTO users (email, password_hash, name, is_admin, permissions)
                VALUES (?, ?, ?, ?, ?)
                """,
                (email, password_hash, name, is_admin, json.dumps(permissions))
            )
            logger.info(f"Created user: {email} (admin: {is_admin})")
            return user_id
        except aiosqlite.IntegrityError:
            logger.error(f"User already exists: {email}")
            return None

    async def create_oauth_user(
        self,
        email: str,
        name: Optional[str] = None
    ) -> Optional[int]:
        """
        Create a new OAuth2 user (without password).

        Args:
            email: User email
            name: User name

        Returns:
            User ID if successful, None if user already exists.
        """
        return await self.create_user(email, password_hash=None, name=name, is_admin=False)

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email.

        Returns:
            User dict if found, None otherwise.
        """
        row = await self._execute_query(
            "SELECT * FROM users WHERE email = ?",
            (email,),
            fetch_one=True
        )
        return dict(row) if row else None

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID.

        Returns:
            User dict if found, None otherwise.
        """
        row = await self._execute_query(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
            fetch_one=True
        )
        return dict(row) if row else None

    async def update_user_last_login(self, user_id: int) -> None:
        """Update user's last login time."""
        await self._execute_update(
            """
            UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?
            """,
            (user_id,)
        )

    async def get_user_language(self, user_id: int) -> Optional[str]:
        """Get user's language preference.

        Returns:
            Language code if found, "en-US" as default.
        """
        row = await self._execute_query(
            "SELECT language FROM users WHERE id = ?",
            (user_id,),
            fetch_one=True
        )

        # sqlite3.Row doesn't support .get() method, use index or column name access
        if row and row[0]:
            return row[0]

        return "en-US"

    async def update_user_language(self, user_id: int, language: str) -> None:
        """Update user's language preference."""
        await self._execute_update(
            """
            UPDATE users SET language = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
            """,
            (language, user_id)
        )
        logger.info(f"Updated language for user {user_id}: {language}")

    async def update_user_password(self, user_id: int, password_hash: str) -> None:
        """Update user's password."""
        await self._execute_update(
            """
            UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
            """,
            (password_hash, user_id)
        )
        logger.info(f"Updated password for user {user_id}")

    async def update_user(
        self,
        user_id: int,
        email: Optional[str] = None,
        name: Optional[str] = None,
        is_admin: Optional[bool] = None,
        is_active: Optional[bool] = None,
        permissions: Optional[str] = None
    ) -> None:
        """Update user fields.

        Args:
            user_id: User ID to update
            email: New email (optional)
            name: New name (optional)
            is_admin: New admin status (optional)
            is_active: New active status (optional)
            permissions: New permissions JSON string (optional)
        """
        set_clauses = []
        params = []

        if email is not None:
            set_clauses.append("email = ?")
            params.append(email)
        if name is not None:
            set_clauses.append("name = ?")
            params.append(name)
        if is_admin is not None:
            set_clauses.append("is_admin = ?")
            params.append(is_admin)
        if is_active is not None:
            set_clauses.append("is_active = ?")
            params.append(is_active)
        if permissions is not None:
            set_clauses.append("permissions = ?")
            params.append(permissions)

        if set_clauses:
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            params.append(user_id)

            await self._execute_update(
                f"UPDATE users SET {', '.join(set_clauses)} WHERE id = ?",
                tuple(params)
            )
            logger.info(f"Updated user {user_id}")

    async def delete_user(self, user_id: int) -> None:
        """Delete user by ID.

        Args:
            user_id: User ID to delete
        """
        await self._execute_update(
            "DELETE FROM users WHERE id = ?",
            (user_id,)
        )
        logger.info(f"Deleted user {user_id}")

    async def get_all_users(self) -> list[Dict[str, Any]]:
        """Get all users.

        Returns:
            List of user dicts ordered by creation date (newest first).
        """
        rows = await self._execute_query(
            """
            SELECT id, email, name, is_admin, is_active, created_at, last_login_at, permissions
            FROM users
            ORDER BY created_at DESC
            """,
            fetch_all=True
        )
        return [dict(row) for row in rows] if rows else []
