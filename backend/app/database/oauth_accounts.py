"""OAuth2 account database operations."""
import aiosqlite
import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class OAuthAccountsManager:
    """Manages OAuth2 accounts in database."""

    def __init__(self, db_core):
        """
        Initialize OAuth accounts manager.

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

    async def create_or_update_oauth_account(
        self,
        user_id: int,
        provider: str,
        provider_user_id: str,
        access_token: str = None,
        refresh_token: str = None,
        token_expires_at: datetime = None,
        raw_user_info: Dict[str, Any] = None
    ) -> Optional[int]:
        """
        Create or update an OAuth account.

        Args:
            user_id: User ID
            provider: OAuth provider (github, google, feishu)
            provider_user_id: Provider-specific user ID
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            token_expires_at: Token expiration timestamp
            raw_user_info: Raw user info from provider

        Returns:
            OAuth account ID
        """
        try:
            # Check if exists
            existing = await self.get_oauth_account(provider, provider_user_id)

            raw_info_json = json.dumps(raw_user_info) if raw_user_info else None
            expires_at_str = token_expires_at.isoformat() if token_expires_at else None

            if existing:
                # Update existing
                await self._execute_update(
                    """
                    UPDATE oauth_accounts
                    SET access_token = ?, refresh_token = ?, token_expires_at = ?,
                        raw_user_info = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (access_token, refresh_token, expires_at_str, raw_info_json, existing['id'])
                )
                logger.info(f"Updated OAuth account: {provider}:{provider_user_id} for user {user_id}")
                return existing['id']
            else:
                # Create new
                oauth_id = await self._execute_update(
                    """
                    INSERT INTO oauth_accounts
                    (user_id, provider, provider_user_id, access_token, refresh_token,
                     token_expires_at, raw_user_info)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, provider, provider_user_id, access_token, refresh_token,
                     expires_at_str, raw_info_json)
                )
                logger.info(f"Created OAuth account: {provider}:{provider_user_id} for user {user_id}")
                return oauth_id
        except aiosqlite.IntegrityError:
            logger.error(f"OAuth account already exists: {provider}:{provider_user_id}")
            return None

    async def get_oauth_account(
        self,
        provider: str,
        provider_user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get OAuth account by provider and provider user ID.

        Args:
            provider: OAuth provider
            provider_user_id: Provider-specific user ID

        Returns:
            OAuth account dict if found, None otherwise
        """
        row = await self._execute_query(
            "SELECT * FROM oauth_accounts WHERE provider = ? AND provider_user_id = ?",
            (provider, provider_user_id),
            fetch_one=True
        )
        return dict(row) if row else None

    async def get_oauth_accounts_by_user(
        self,
        user_id: int
    ) -> list:
        """
        Get all OAuth accounts for a user.

        Args:
            user_id: User ID

        Returns:
            List of OAuth account dicts
        """
        rows = await self._execute_query(
            "SELECT * FROM oauth_accounts WHERE user_id = ?",
            (user_id,),
            fetch_all=True
        )
        return [dict(row) for row in rows]

    async def delete_oauth_account(
        self,
        oauth_account_id: int
    ) -> bool:
        """
        Delete an OAuth account.

        Args:
            oauth_account_id: OAuth account ID

        Returns:
            True if deleted, False otherwise
        """
        rows_affected = await self._execute_update(
            "DELETE FROM oauth_accounts WHERE id = ?",
            (oauth_account_id,)
        )
        logger.info(f"Deleted OAuth account: {oauth_account_id}")
        return rows_affected > 0

    async def get_user_by_oauth(
        self,
        provider: str,
        provider_user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get user by OAuth provider and provider user ID.

        Args:
            provider: OAuth provider
            provider_user_id: Provider-specific user ID

        Returns:
            User dict if found, None otherwise
        """
        row = await self._execute_query(
            """
            SELECT u.* FROM users u
            INNER JOIN oauth_accounts oa ON u.id = oa.user_id
            WHERE oa.provider = ? AND oa.provider_user_id = ?
            """,
            (provider, provider_user_id),
            fetch_one=True
        )
        return dict(row) if row else None

    async def get_user_by_auth_id(
        self,
        provider: str,
        auth_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get user by OAuth provider and auth_id (stored in raw_user_info).

        This is used for providers like Feishu where provider_user_id may change
        but auth_id remains constant.

        Args:
            provider: OAuth provider
            auth_id: The stable user identifier from the OAuth provider

        Returns:
            User dict if found, None otherwise
        """
        # Search through all OAuth accounts for this provider
        # Need to select both user and oauth_account columns to access raw_user_info
        rows = await self._execute_query(
            """
            SELECT u.*, oa.raw_user_info as oauth_raw_user_info
            FROM users u
            INNER JOIN oauth_accounts oa ON u.id = oa.user_id
            WHERE oa.provider = ?
            """,
            (provider,),
            fetch_all=True
        )

        if not rows:
            return None

        # Check each account's raw_user_info for the auth_id
        for row in rows:
            try:
                import json
                # sqlite3.Row doesn't have .get(), use dict() conversion
                row_dict = dict(row)
                raw_info_str = row_dict.get("oauth_raw_user_info") or "{}"
                raw_info = json.loads(raw_info_str)
                if raw_info.get("auth_id") == auth_id:
                    # Return the user dict (without oauth columns)
                    user_dict = {k: v for k, v in row_dict.items() if k != "oauth_raw_user_info"}
                    return user_dict
            except (json.JSONDecodeError, TypeError, KeyError):
                continue

        return None
