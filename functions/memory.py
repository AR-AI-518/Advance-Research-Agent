import uuid

from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.store.base import BaseStore

from layers.config import get_settings


class MakeMem(BaseModel):
    text: str = Field(description="Atomic user memory as short answer")
    is_new: bool = Field(
        description="True if memory is not already present in saved memories"
    )


class MakeDes(BaseModel):
    should_write: bool = Field(
        description="True only if useful long-term user information exists"
    )
    memory: list[MakeMem] = Field(
        description="Short, useful long-term facts about the user"
    )


class MemoryManager:
    def __init__(self):
        settings = get_settings()

        self.llm = ChatOpenAI(
            model=settings.base_model,
            api_key=settings.Open_Api_Key
        )

        self.mem_llm = self.llm.with_structured_output(MakeDes)
        self.chats = {}

    def make_memory(
        self,
        user_message: str,
        config: RunnableConfig,
        store: BaseStore
    ):
        user_id = config["configurable"]["user_id"]
        namespace = ("users", user_id, "details")

        saved_memories = store.search(namespace)

        if saved_memories:
            existing_memory = "\n".join(
                f"- {item.value.get('data', '')}"
                for item in saved_memories
            )
        else:
            existing_memory = "No saved memory."

        decision: MakeDes = self.mem_llm.invoke(
            [
                SystemMessage(
                    content="""
Extract only useful long-term information about the user.

Store facts such as:
- Name
- Skills
- Preferences
- Goals
- Projects
- Important personal choices

Do not store greetings, temporary questions, or unnecessary details.
Compare with existing memories and set is_new to False for duplicates.
Set should_write to False if no useful memory exists.
"""
                ),
                HumanMessage(
                    content=f"""
Existing saved memories:
{existing_memory}

New user message:
{user_message}
"""
                )
            ]
        )

        if decision.should_write:
            for item in decision.memory:
                if item.is_new:
                    store.put(
                        namespace,
                        str(uuid.uuid4()),
                        {"data": item.text}
                    )

    def get_user_memory(
        self,
        config: RunnableConfig,
        store: BaseStore
    ) -> str:
        user_id = config["configurable"]["user_id"]
        namespace = ("users", user_id, "details")

        memories = store.search(namespace)

        if not memories:
            return "No saved memory."

        return "\n".join(
            f"- {item.value.get('data', '')}"
            for item in memories
        )

    def generate_title(self, message: str) -> str:
        title_llm = self.llm.invoke(
            f"""
Create a very short chat title for this user message.

Rules:
- Maximum 5 words
- No quotes
- Only return title
- Make it descriptive

User message:
{message}
"""
        )

        return title_llm.content.strip()

    def create_chat(self, first_message: str) -> str:
        thread_id = str(uuid.uuid4())
        title = self.generate_title(first_message)

        self.chats[thread_id] = {
            "title": title
        }

        return thread_id

    def make_thread(self, query: str, user_id: str) -> RunnableConfig:
        thread_id = self.create_chat(query)

        config = {
            "configurable": {
                "thread_id": thread_id,
                "user_id": user_id
            }
        }

        return config