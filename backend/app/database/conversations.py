"""Conversations database operations for chat history management."""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# Beijing timezone constant
BEIJING_TZ = timezone(timedelta(hours=8))


def _convert_to_beijing_iso(dt_value) -> Optional[str]:
    """Convert a datetime value to Beijing timezone ISO format string.

    Args:
        dt_value: Datetime object or string from database

    Returns:
        ISO format string in Beijing timezone, or None if input is None/invalid
    """
    if dt_value is None:
        return None

    try:
        if hasattr(dt_value, 'astimezone'):
            # Already a datetime object, convert to Beijing timezone
            beijing_dt = dt_value.astimezone(BEIJING_TZ)
            return beijing_dt.isoformat()
        else:
            # String format, parse as UTC then convert to Beijing
            utc_str = str(dt_value).replace(' ', 'T') + 'Z'
            utc_dt = datetime.fromisoformat(utc_str)
            beijing_dt = utc_dt.astimezone(BEIJING_TZ)
            return beijing_dt.isoformat()
    except Exception:
        return None


class ConversationsManager:
    """Manages conversations and messages in the database."""

    def __init__(self, db_core):
        """
        Initialize conversations manager.

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

    async def create_conversation(
        self,
        user_id: int,
        title: str,
        provider_name: Optional[str] = None,
        api_format: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Optional[int]:
        """
        Create a new conversation.

        Args:
            user_id: User ID who owns this conversation
            title: Conversation title
            provider_name: Provider name
            api_format: API format (openai/anthropic)
            model: Model name

        Returns:
            Conversation ID if successful, None otherwise
        """
        try:
            conversation_id = await self._execute_update(
                """
                INSERT INTO conversations (user_id, title, provider_name, api_format, model)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, title, provider_name, api_format, model)
            )
            logger.info(f"Created conversation {conversation_id} for user {user_id}")
            return conversation_id
        except Exception as e:
            logger.error(f"Failed to create conversation: {e}")
            return None

    async def get_conversations(
        self,
        user_id: int,
        limit: Optional[int] = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get conversations for a user.

        Args:
            user_id: User ID
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of conversation records
        """
        try:
            # Single query with subquery for last_model (no N+1 issue)
            rows = await self._execute_query(
                """
                SELECT
                    c.id,
                    c.title,
                    c.provider_name,
                    c.api_format,
                    c.model,
                    c.created_at,
                    c.updated_at,
                    (
                        SELECT m.model
                        FROM conversation_messages m
                        WHERE m.conversation_id = c.id
                        AND m.role = 'user'
                        ORDER BY m.id DESC
                        LIMIT 1
                    ) as last_model
                FROM conversations c
                WHERE c.user_id = ?
                ORDER BY c.updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (user_id, limit, offset),
                fetch_all=True
            )

            conversations = []
            for row in rows:
                conversations.append({
                    "id": row["id"],
                    "title": row["title"],
                    "provider_name": row["provider_name"],
                    "api_format": row["api_format"],
                    "model": row["model"],
                    "last_model": row["last_model"],
                    "created_at": _convert_to_beijing_iso(row["created_at"]),
                    "updated_at": _convert_to_beijing_iso(row["updated_at"]),
                })

            return conversations
        except Exception as e:
            logger.error(f"Failed to get conversations: {e}")
            return []

    async def get_conversation(
        self, conversation_id: int, user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific conversation by ID.

        Args:
            conversation_id: Conversation ID
            user_id: User ID (for security check)

        Returns:
            Conversation record with messages if found and belongs to user
        """
        try:
            # Single query combining all subqueries (fixes N+1 issue)
            row = await self._execute_query(
                """
                SELECT
                    c.id,
                    c.title,
                    c.provider_name,
                    c.api_format,
                    c.model,
                    c.created_at,
                    c.updated_at,
                    (
                        SELECT m.model
                        FROM conversation_messages m
                        WHERE m.conversation_id = c.id
                        AND m.role = 'user'
                        ORDER BY m.id DESC
                        LIMIT 1
                    ) as last_model,
                    (
                        SELECT m.provider_name
                        FROM conversation_messages m
                        WHERE m.conversation_id = c.id
                        AND m.role = 'user'
                        ORDER BY m.id DESC
                        LIMIT 1
                    ) as last_provider_name,
                    (
                        SELECT m.api_format
                        FROM conversation_messages m
                        WHERE m.conversation_id = c.id
                        AND m.role = 'user'
                        ORDER BY m.id DESC
                        LIMIT 1
                    ) as last_api_format
                FROM conversations c
                WHERE c.id = ? AND c.user_id = ?
                """,
                (conversation_id, user_id),
                fetch_one=True
            )

            if not row:
                return None

            conversation = {
                "id": row["id"],
                "title": row["title"],
                "provider_name": row["provider_name"],
                "api_format": row["api_format"],
                "model": row["model"],
                "last_model": row["last_model"],
                "last_provider_name": row["last_provider_name"],
                "last_api_format": row["last_api_format"],
                "created_at": _convert_to_beijing_iso(row["created_at"]),
                "updated_at": _convert_to_beijing_iso(row["updated_at"]),
                "messages": [],
            }

            # Get messages for this conversation
            message_rows = await self._execute_query(
                """
                SELECT id, role, content, model, thinking, input_tokens, output_tokens,
                       created_at, provider_name, api_format, parent_message_id, model_instance_index
                FROM conversation_messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                """,
                (conversation_id,),
                fetch_all=True
            )

            for msg_row in message_rows:
                conversation["messages"].append({
                    "id": msg_row["id"],
                    "role": msg_row["role"],
                    "content": msg_row["content"],
                    "model": msg_row["model"],
                    "thinking": msg_row["thinking"],
                    "input_tokens": msg_row["input_tokens"],
                    "output_tokens": msg_row["output_tokens"],
                    "provider_name": msg_row["provider_name"],
                    "api_format": msg_row["api_format"],
                    "parent_message_id": msg_row["parent_message_id"],
                    "model_instance_index": msg_row["model_instance_index"] or 0,
                    "created_at": _convert_to_beijing_iso(msg_row["created_at"]),
                })

            return conversation
        except Exception as e:
            logger.error(f"Failed to get conversation {conversation_id}: {e}")
            return None

    async def update_conversation(
        self, conversation_id: int, user_id: int, title: str
    ) -> bool:
        """
        Update conversation title.

        Args:
            conversation_id: Conversation ID
            user_id: User ID (for security check)
            title: New title

        Returns:
            True if successful, False otherwise
        """
        row_count = await self._execute_update(
            """
            UPDATE conversations
            SET title = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (title, conversation_id, user_id)
        )
        if row_count > 0:
            logger.info(f"Updated conversation {conversation_id} title")
        return row_count > 0

    async def delete_conversation(self, conversation_id: int, user_id: int) -> bool:
        """
        Delete a conversation and its messages.

        Args:
            conversation_id: Conversation ID
            user_id: User ID (for security check)

        Returns:
            True if successful, False otherwise
        """
        row_count = await self._execute_update(
            """
            DELETE FROM conversations
            WHERE id = ? AND user_id = ?
            """,
            (conversation_id, user_id)
        )
        if row_count > 0:
            logger.info(f"Deleted conversation {conversation_id}")
        return row_count > 0

    async def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        model: Optional[str] = None,
        thinking: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        provider_name: Optional[str] = None,
        api_format: Optional[str] = None,
        parent_message_id: Optional[int] = None,
        model_instance_index: Optional[int] = None,
    ) -> Optional[int]:
        """
        Add a message to a conversation.

        Args:
            conversation_id: Conversation ID
            role: Message role ('user' or 'assistant')
            content: Message content
            model: Model used for this message
            thinking: Extended thinking content (optional)
            input_tokens: Input token count
            output_tokens: Output token count
            provider_name: Provider used for this message
            api_format: API format for this message (optional)
            parent_message_id: ID of the parent message (optional)
            model_instance_index: Index of the model instance for multi-model scenarios (optional)

        Returns:
            Message ID if successful, None otherwise
        """
        conn = None
        cursor = None
        try:
            conn = await self.db_core.get_connection()
            cursor = await conn.cursor()
            # Insert new message
            await cursor.execute(
                """
                INSERT INTO conversation_messages
                (conversation_id, role, content, provider_name, model, thinking, input_tokens, output_tokens, api_format, parent_message_id, model_instance_index)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (conversation_id, role, content, provider_name, model, thinking, input_tokens, output_tokens, api_format, parent_message_id, model_instance_index or 0),
            )
            message_id = cursor.lastrowid

            # Update conversation updated_at
            await cursor.execute(
                """
                UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?
                """,
                (conversation_id,),
            )

            await conn.commit()
            logger.debug(f"Added message {message_id} to conversation {conversation_id}")
            return message_id
        except Exception as e:
            logger.error(f"Failed to add message to conversation {conversation_id}: {e}")
            return None
        finally:
            if cursor is not None:
                try:
                    await cursor.close()
                except Exception:
                    pass
            if conn is not None:
                await self.db_core.release_connection(conn)

    async def get_messages(
        self, conversation_id: int, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get messages for a conversation.

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages (None for all)

        Returns:
            List of message records
        """
        try:
            query = """
                SELECT id, role, content, model, thinking, input_tokens, output_tokens,
                       created_at, provider_name, api_format, parent_message_id, model_instance_index
                FROM conversation_messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
            """
            params = [conversation_id]

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            rows = await self._execute_query(query, tuple(params), fetch_all=True)

            messages = []
            for row in rows:
                messages.append({
                    "id": row["id"],
                    "role": row["role"],
                    "content": row["content"],
                    "model": row["model"],
                    "thinking": row["thinking"],
                    "input_tokens": row["input_tokens"],
                    "output_tokens": row["output_tokens"],
                    "provider_name": row["provider_name"],
                    "api_format": row["api_format"],
                    "parent_message_id": row["parent_message_id"],
                    "model_instance_index": row["model_instance_index"] or 0,
                    "created_at": _convert_to_beijing_iso(row["created_at"]),
                })

            return messages
        except Exception as e:
            logger.error(f"Failed to get messages for conversation {conversation_id}: {e}")
            return []

    async def delete_old_conversations(self, days: int = 30) -> int:
        """
        Delete conversations older than specified days.

        Args:
            days: Number of days

        Returns:
            Number of deleted conversations
        """
        row_count = await self._execute_update(
            """
            DELETE FROM conversations
            WHERE updated_at < datetime('now', '-' || ? || ' days')
            """,
            (days,)
        )
        if row_count > 0:
            logger.info(f"Deleted {row_count} old conversations")
        return row_count
