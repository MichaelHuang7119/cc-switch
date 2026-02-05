"""Data models for Anthropic API compatibility."""

from typing import List, Optional, Union, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class MessageRole(str, Enum):
    """Message role types."""

    USER = "user"
    ASSISTANT = "assistant"


class TextContent(BaseModel):
    """Text content block."""

    type: Literal["text"] = "text"
    text: str


class ImageSourceType(str, Enum):
    """Image source type."""

    BASE64 = "base64"
    URL = "url"


class ImageSource(BaseModel):
    """Image source."""

    type: ImageSourceType
    media_type: Optional[str] = Field(None, alias="media_type")
    data: Optional[str] = None
    url: Optional[str] = None


class ImageContent(BaseModel):
    """Image content block."""

    type: Literal["image"] = "image"
    source: ImageSource


class TextDelta(BaseModel):
    """Text delta in streaming response."""

    type: Literal["text_delta"] = "text_delta"
    text: str


class ContentBlock(BaseModel):
    """Content block."""

    type: str
    text: Optional[str] = None
    source: Optional[ImageSource] = None
    name: Optional[str] = None
    input: Optional[Dict[str, Any]] = None
    id: Optional[str] = None  # For tool_use blocks
    model_config = {"extra": "allow"}  # Allow extra fields


class Message(BaseModel):
    """Anthropic message."""

    role: MessageRole
    content: Union[str, List[Union[TextContent, ImageContent, ContentBlock]]]


class ToolDefinition(BaseModel):
    """Tool definition."""

    name: str
    description: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = Field(None, alias="input_schema")


class MessagesRequest(BaseModel):
    """Anthropic messages request."""

    model: str
    messages: List[Message]
    max_tokens: int
    metadata: Optional[Dict[str, Any]] = None
    stop_sequences: Optional[List[str]] = None
    stream: Optional[bool] = False
    system: Optional[Union[str, List[Union[TextContent, Dict[str, Any]]]]] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    tools: Optional[List[ToolDefinition]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None  # Optional per spec
    container: Optional[Union[str, Dict[str, Any]]] = None  # Optional per spec
    context_management: Optional[Dict[str, Any]] = None  # Optional per spec
    mcp_servers: Optional[List[Dict[str, Any]]] = None  # Optional per spec
    service_tier: Optional[Literal["auto", "standard_only"]] = None  # Optional per spec
    thinking: Optional[Dict[str, Any]] = None  # Optional per spec
    provider: Optional[str] = None  # Optional: specify provider name to use

    model_config = ConfigDict(extra="allow")


class TextBlock(BaseModel):
    """Text block in response."""

    type: Literal["text"] = "text"
    text: str
    citations: Optional[Any] = None  # Optional citations field per Anthropic spec


class ToolUseBlock(BaseModel):
    """Tool use block in response."""

    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: Dict[str, Any]


class ToolResultBlock(BaseModel):
    """Tool result block."""

    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: Union[str, List[TextBlock]]
    is_error: Optional[bool] = False


class MessageResponse(BaseModel):
    """Anthropic message response."""

    id: str
    type: Literal["message"] = "message"
    role: Literal["assistant"] = "assistant"
    content: List[Union[TextBlock, ToolUseBlock]]
    model: str
    stop_reason: Optional[str] = None
    stop_sequence: Optional[str] = None
    usage: Dict[str, int]
    context_management: Optional[Dict[str, Any]] = None  # Optional per spec
    container: Optional[Dict[str, Any]] = None  # Optional per spec

    model_config = {"protected_namespaces": ()}


class StreamResponse(BaseModel):
    """Anthropic streaming response."""

    type: str
    delta: Optional[TextDelta] = None
    content_block: Optional[Union[TextBlock, ToolUseBlock]] = None
    content_block_delta: Optional[TextDelta] = None
    message: Optional[MessageResponse] = None
    usage: Optional[Dict[str, int]] = None


class CountTokensRequest(BaseModel):
    """Count tokens request."""

    model: str
    messages: List[Message]


class CountTokensResponse(BaseModel):
    """Count tokens response."""

    model: str
    input_tokens: int
