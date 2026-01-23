"""Conversation management API endpoints."""
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends, Query

from ..core.auth import require_user, require_conversations

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

def format_datetime(dt_str: str | None) -> str | None:
    """Convert datetime string to Beijing time ISO format."""
    if not dt_str:
        return None

    try:
        from datetime import datetime, timezone, timedelta

        # 北京时区 (UTC+8)
        beijing_tz = timezone(timedelta(hours=8))

        # 处理不同格式
        if ' ' in dt_str and 'T' not in dt_str:
            # SQLite格式: "2025-11-28 07:54:15"
            utc_str = dt_str.replace(' ', 'T') + 'Z'
            utc_dt = datetime.fromisoformat(utc_str)
        elif dt_str.endswith('Z'):
            # UTC ISO格式: "2025-11-28T07:54:15Z"
            utc_dt = datetime.fromisoformat(dt_str[:-1])
        else:
            # 其他格式，尝试直接解析
            utc_dt = datetime.fromisoformat(dt_str)

        # 转换为北京时间
        beijing_dt = utc_dt.astimezone(beijing_tz)
        return beijing_dt.isoformat()
    except Exception:
        return dt_str

class ConversationCreate(BaseModel):
    """Create conversation request model."""
    title: str
    provider_name: Optional[str] = None
    api_format: Optional[str] = "openai"
    model: str

class ConversationUpdate(BaseModel):
    """Update conversation request model."""
    title: str

class MessageCreate(BaseModel):
    """Create message request model."""
    role: str
    content: str
    model: Optional[str] = None
    thinking: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    provider_name: Optional[str] = None
    api_format: Optional[str] = None
    parent_message_id: Optional[int] = None
    model_instance_index: Optional[int] = None

class ConversationResponse(BaseModel):
    """Conversation response model."""
    id: int
    title: str
    provider_name: Optional[str]
    api_format: Optional[str]
    model: Optional[str]
    last_model: Optional[str] = Field(None, description="Last user message model")
    created_at: Optional[str] = Field(None, description="ISO 8601 Beijing time (UTC+8)")
    updated_at: Optional[str] = Field(None, description="ISO 8601 Beijing time (UTC+8)")

class MessageResponse(BaseModel):
    """Message response model."""
    id: int
    role: str
    content: str
    thinking: Optional[str] = None
    model: Optional[str]
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    created_at: Optional[str] = Field(None, description="ISO 8601 Beijing time (UTC+8)")
    provider_name: Optional[str]
    api_format: Optional[str]
    parent_message_id: Optional[int] = None
    model_instance_index: Optional[int] = None

class ConversationDetailResponse(BaseModel):
    """Detailed conversation response with messages."""
    id: int
    title: str
    provider_name: Optional[str]
    api_format: Optional[str]
    model: Optional[str]
    last_model: Optional[str] = Field(None, description="Last user message model")
    last_provider_name: Optional[str] = Field(None, description="Last user message provider")
    last_api_format: Optional[str] = Field(None, description="Last user message API format")
    created_at: Optional[str] = Field(None, description="ISO 8601 Beijing time (UTC+8)")
    updated_at: Optional[str] = Field(None, description="ISO 8601 Beijing time (UTC+8)")
    messages: List[MessageResponse]

@router.get("", response_model=List[ConversationResponse])
async def get_conversations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(require_conversations())
):
    """
    Get conversations for current user.

    Args:
        limit: Maximum number of results (1-200)
        offset: Pagination offset
        user: Current authenticated user
    """
    try:
        from ..database import get_database
        db = get_database()

        user_id = user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        conversations = await db.conversations.get_conversations(
            user_id=user_id, limit=limit, offset=offset
        )

        # 标准化时间格式
        formatted_conversations = []
        for conv in conversations:
            formatted_conversations.append({
                **conv,
                "created_at": format_datetime(conv["created_at"]),
                "updated_at": format_datetime(conv["updated_at"])
            })

        return formatted_conversations
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get conversations: {str(e)}")

@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    conversation: ConversationCreate,
    user: dict = Depends(require_conversations())
):
    """
    Create a new conversation.

    Args:
        conversation: Conversation creation data
        user: Current authenticated user
    """
    try:
        from ..database import get_database
        db = get_database()

        user_id = user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        # Create conversation
        conversation_id = await db.conversations.create_conversation(
            user_id=user_id,
            title=conversation.title,
            provider_name=conversation.provider_name,
            api_format=conversation.api_format,
            model=conversation.model
        )

        if not conversation_id:
            raise HTTPException(status_code=500, detail="Failed to create conversation")

        # Get the created conversation
        conversation_data = await db.conversations.get_conversation(conversation_id, user_id)
        if not conversation_data:
            raise HTTPException(status_code=500, detail="Failed to retrieve created conversation")

        # 标准化时间格式
        formatted_data = {
            **conversation_data,
            "created_at": format_datetime(conversation_data["created_at"]),
            "updated_at": format_datetime(conversation_data["updated_at"])
        }

        return formatted_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(e)}")

@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: int,
    user: dict = Depends(require_conversations())
):
    """
    Get a specific conversation with messages.

    Args:
        conversation_id: Conversation ID
        user: Current authenticated user
    """
    try:
        from ..database import get_database
        db = get_database()

        user_id = user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        conversation = await db.conversations.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # 标准化时间格式
        formatted_conversation = {
            "id": conversation["id"],
            "title": conversation["title"],
            "provider_name": conversation["provider_name"],
            "api_format": conversation["api_format"],
            "model": conversation["model"],
            "last_model": conversation.get("last_model"),
            "last_provider_name": conversation.get("last_provider_name"),
            "last_api_format": conversation.get("last_api_format"),
            "created_at": format_datetime(conversation["created_at"]),
            "updated_at": format_datetime(conversation["updated_at"]),
            "messages": []
        }

        # 格式化消息时间
        for msg in conversation["messages"]:
            formatted_conversation["messages"].append({
                **msg,
                "created_at": format_datetime(msg["created_at"])
            })

        return formatted_conversation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {str(e)}")

@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    update: ConversationUpdate,
    user: dict = Depends(require_conversations())
):
    """
    Update conversation (rename).

    Args:
        conversation_id: Conversation ID
        update: Update data (title)
        user: Current authenticated user
    """
    try:
        from ..database import get_database
        db = get_database()

        user_id = user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        success = await db.conversations.update_conversation(
            conversation_id, user_id, update.title
        )

        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found or update failed")

        # Return updated conversation
        conversation = await db.conversations.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found after update")

        # 标准化时间格式
        formatted_conversation = {
            **conversation,
            "created_at": format_datetime(conversation["created_at"]),
            "updated_at": format_datetime(conversation["updated_at"])
        }

        return formatted_conversation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update conversation: {str(e)}")

@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: int,
    user: dict = Depends(require_conversations())
):
    """
    Delete a conversation and all its messages.

    Args:
        conversation_id: Conversation ID
        user: Current authenticated user
    """
    try:
        from ..database import get_database
        db = get_database()

        user_id = user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        success = await db.conversations.delete_conversation(conversation_id, user_id)

        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found or delete failed")

        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")

@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=201)
async def add_message(
    conversation_id: int,
    message_data: MessageCreate,
    user: dict = Depends(require_conversations())
):
    """
    Add a message to a conversation.

    Args:
        conversation_id: Conversation ID
        message_data: Message creation data
        user: Current authenticated user
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        from ..database import get_database
        db = get_database()

        user_id = user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        # Validate role
        if message_data.role not in ["user", "assistant"]:
            raise HTTPException(status_code=400, detail="Role must be 'user' or 'assistant'")

        # Validate content
        if not message_data.content or not message_data.content.strip():
            raise HTTPException(status_code=400, detail="Content cannot be empty")

        # Log message being added
        content_preview = message_data.content[:200] if len(message_data.content) > 200 else message_data.content
        logger.info(
            f"Adding message to conversation {conversation_id}:\n"
            f"  Role: {message_data.role}\n"
            f"  Model: {message_data.model}\n"
            f"  Content: {content_preview}{'...' if len(message_data.content) > 200 else ''}\n"
            f"  Has Thinking: {bool(message_data.thinking)}"
        )

        # Verify conversation belongs to user
        conversation = await db.conversations.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Add message
        message_id = await db.conversations.add_message(
            conversation_id=conversation_id,
            role=message_data.role,
            content=message_data.content,
            model=message_data.model,
            thinking=message_data.thinking,
            input_tokens=message_data.input_tokens,
            output_tokens=message_data.output_tokens,
            provider_name=message_data.provider_name,
            api_format=message_data.api_format,
            parent_message_id=message_data.parent_message_id,
            model_instance_index=message_data.model_instance_index,
        )

        if not message_id:
            raise HTTPException(status_code=500, detail="Failed to add message")

        # Get the created message (simplified retrieval)
        messages = await db.conversations.get_messages(conversation_id)
        for msg in messages:
            if msg["id"] == message_id:
                # 标准化返回的消息时间格式
                formatted_msg = {
                    **msg,
                    "created_at": format_datetime(msg["created_at"])
                }
                return formatted_msg

        raise HTTPException(status_code=500, detail="Failed to retrieve created message")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add message: {str(e)}")

@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: int,
    limit: Optional[int] = Query(None, ge=1, le=1000),
    user: dict = Depends(require_conversations())
):
    """
    Get messages for a conversation.

    Args:
        conversation_id: Conversation ID
        limit: Maximum number of messages
        user: Current authenticated user
    """
    try:
        from ..database import get_database
        db = get_database()

        user_id = user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        # Verify conversation belongs to user
        conversation = await db.conversations.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        messages = await db.conversations.get_messages(conversation_id, limit)

        # 标准化消息时间格式
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                **msg,
                "created_at": format_datetime(msg["created_at"])
            })

        return formatted_messages
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get messages: {str(e)}")
