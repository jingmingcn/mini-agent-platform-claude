"""Import all models so Base.metadata is complete (used by Alembic / create_all)."""
from app.models.agent import Agent, AgentKnowledgeBase, AgentPrompt, UserAgentPermission
from app.models.conversation import Conversation, Message, UploadedFile
from app.models.knowledge import Document, DocumentChunk, KnowledgeBase
from app.models.llm_config import LLMConfig
from app.models.log import ApiLog, AuditLog, SystemSetting, UsageStatistic
from app.models.user import AdminUser, User

__all__ = [
    "AdminUser", "User", "LLMConfig", "Agent", "AgentKnowledgeBase", "UserAgentPermission", "AgentPrompt",
    "KnowledgeBase", "Document", "DocumentChunk", "Conversation", "Message", "UploadedFile",
    "ApiLog", "UsageStatistic", "AuditLog", "SystemSetting",
]
