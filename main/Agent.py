from layers.config import get_settings
from functions.memory import MemoryManager
from functions.planning import createPlan
from functions.tools import get_search, get_information
from functions.prompts import URL_SEARCH_PROMPT, DETAILED_RESEARCH_PROMPT

from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langsmith import traceable

from pydantic import BaseModel, Field
from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages
import json

memory = InMemoryStore()
checkpointer = MemorySaver()

class FromUrl(BaseModel):
    urls: list[str] = Field(description="List of relevant, valid source URLs.")
    snippets: list[str] = Field(description="A concise explanation of each source in 2-3 sentences.")
    titles: list[str] = Field(description="Short, descriptive titles corresponding to each source.")

class MakeResearch(BaseModel):
    query: str = Field(description="The user's original research question.")
    summary: str = Field(description="A concise, factual summary of the research findings.")
    key_findings: list[str] = Field(description="Important findings supported by the collected sources.")
    sources: list[FromUrl] = Field(description="Source URLs, titles, and snippets used in the research.")
    limitations: list[str] = Field(default_factory=list, description="Missing information, conflicting evidence, or research limitations.")

class StateClass(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    Urls: Optional[list[str]]
    snippets: list[str]
    titles: list[str]
    planing: list
    memory: object
    research_result: Optional[MakeResearch]
    retry_countSimpleSearch: int
    retry_countResearch: int
    error: Optional[str]
    model_used: list[str]
    input_tokens: int
    output_tokens: int

class Research:
    def __init__(self):
        self.setting = get_settings()
        self.tools = [get_search, get_information]
        self.tool_map = {tool.name: tool for tool in self.tools}
        self.tool_node = ToolNode(self.tools)
        self.tool_node = ToolNode(self.tools)

        self.baseModel = ChatOpenAI(
            model=self.setting.base_model,
            api_key=self.setting.Open_Api_Key,
            temperature=0,
            timeout=30,
            max_retries=0
        )

        self.fallbackModel = ChatOpenAI(
            model=self.setting.fall_back_model,
            api_key=self.setting.Open_Api_Key,
            temperature=0,
            timeout=30,
            max_retries=0
        )

        self.BaseTool = self.baseModel.bind_tools(tools=self.tools)
        self.FallBackTool = self.fallbackModel.bind_tools(tools=self.tools)

        self.BaseUrl = self.baseModel.with_structured_output(FromUrl, include_raw=True)
        self.FallBackUrl = self.fallbackModel.with_structured_output(FromUrl, include_raw=True)

        self.BaseResearch = self.baseModel.with_structured_output(MakeResearch, include_raw=True)
        self.FallBackResearch = self.fallbackModel.with_structured_output(MakeResearch, include_raw=True)

        self.graph = self.builgGraph()

    @staticmethod
    def get_query(state: StateClass) -> str:
        for message in reversed(state.get("messages", [])):
            if isinstance(message, HumanMessage):
                return str(message.content)
        raise ValueError("No human message found in state.")

    @staticmethod
    def get_usage(response: dict) -> dict:
        raw = response.get("raw")
        return getattr(raw, "usage_metadata", None) or {}

    @staticmethod
    def validate_response(response: dict):
        if response.get("parsing_error"):
            raise ValueError(str(response["parsing_error"]))
        result = response.get("parsed")
        if result is None:
            raise ValueError("Structured output was not returned.")
        return result


    def _run_tools(self, model, system_prompt: str, query: str):
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=query)
        ]
        total_input_tokens = 0
        total_output_tokens = 0

        for _ in range(4):
            response = model.invoke(messages)
            usage = getattr(response, "usage_metadata", None) or {}
            total_input_tokens += usage.get("input_tokens", 0)
            total_output_tokens += usage.get("output_tokens", 0)
            messages.append(response)

            route = tools_condition({"messages": [response]})
            if route != "tools":
                break

            tool_result = self.tool_node.invoke({"messages": [response]})
            messages.extend(tool_result.get("messages", []))

        return messages, total_input_tokens, total_output_tokens

    def MakeMemory(self, state: StateClass) -> dict:
        userMessage = HumanMessage(content=self.get_query(state))
        makeMem = MemoryManager.make_memory(userMessage)
        return {"memory": makeMem}

    def makePlan(self, state: StateClass) -> dict:
        userMessage = HumanMessage(content=self.get_query(state))
        plan = createPlan(userMessage)
        return {"planing": plan}

    def makeBaseSearch(self, state: StateClass) -> dict:
        try:
            query = self.get_query(state)
            plan = state.get("planing", [])
            user_memory = MemoryManager.get_user_memory()
            system_prompt = f"{URL_SEARCH_PROMPT}\n\nPlan:\n{plan}\n\nMemory:\n{user_memory}"

            tool_messages, tool_input_tokens, tool_output_tokens = self._run_tools(
                self.BaseTool, system_prompt, query
            )

            BaseResponse = self.BaseUrl.invoke(tool_messages)
            result = self.validate_response(BaseResponse)
            usage = self.get_usage(BaseResponse)

            return {
                "Urls": result.urls,
                "snippets": result.snippets,
                "titles": result.titles,
                "model_used": [self.setting.base_model],
                "error": None,
                "retry_countSimpleSearch": state.get("retry_countSimpleSearch", 0),
                "input_tokens": state.get("input_tokens", 0) + tool_input_tokens + usage.get("input_tokens", 0),
                "output_tokens": state.get("output_tokens", 0) + tool_output_tokens + usage.get("output_tokens", 0)
            }
        except Exception as e:
            return {
                "error": str(e),
                "retry_countSimpleSearch": state.get("retry_countSimpleSearch", 0) + 1
            }

    def UseFallBackSearch(self, state: StateClass) -> dict:
        try:
            query = self.get_query(state)
            plan = state.get("planing", [])
            user_memory = MemoryManager.get_user_memory()
            system_prompt = f"{URL_SEARCH_PROMPT}\n\nPlan:\n{plan}\n\nMemory:\n{user_memory}"

            tool_messages, tool_input_tokens, tool_output_tokens = self._run_tools(
                self.FallBackTool, system_prompt, query
            )

            FallBackResponse = self.FallBackUrl.invoke(tool_messages)
            result = self.validate_response(FallBackResponse)
            usage = self.get_usage(FallBackResponse)

            return {
                "Urls": result.urls,
                "snippets": result.snippets,
                "titles": result.titles,
                "model_used": [self.setting.fall_back_model],
                "error": None,
                "input_tokens": state.get("input_tokens", 0) + tool_input_tokens + usage.get("input_tokens", 0),
                "output_tokens": state.get("output_tokens", 0) + tool_output_tokens + usage.get("output_tokens", 0)
            }
        except Exception as e:
            return {"error": str(e)}

    def makeBaseResearch(self, state: StateClass) -> dict:
        try:
            query = self.get_query(state)
            plan = state.get("planing", [])
            Urls = state.get("Urls") or []
            Snipits = state.get("snippets", [])
            Title = state.get("titles", [])
            user_memory = MemoryManager.get_user_memory()

            BaseResponse = self.BaseResearch.invoke([
                SystemMessage(content=(
                    f"{DETAILED_RESEARCH_PROMPT}\n\n"
                    f"Plan:\n{plan}\n\n"
                    f"URLs:\n{Urls}\n\n"
                    f"Snippets:\n{Snipits}\n\n"
                    f"Titles:\n{Title}\n\n"
                    f"Memory:\n{user_memory}"
                )),
                HumanMessage(content=query)
            ])

            result = self.validate_response(BaseResponse)
            usage = self.get_usage(BaseResponse)

            return {
                "research_result": result,
                "model_used": [self.setting.base_model],
                "error": None,
                "retry_countResearch": state.get("retry_countResearch", 0),
                "input_tokens": state.get("input_tokens", 0) + usage.get("input_tokens", 0),
                "output_tokens": state.get("output_tokens", 0) + usage.get("output_tokens", 0)
            }
        except Exception as e:
            return {
                "retry_countResearch": state.get("retry_countResearch", 0) + 1,
                "error": str(e)
            }

    def makeFallResearch(self, state: StateClass) -> dict:
        try:
            query = self.get_query(state)
            plan = state.get("planing", [])
            Urls = state.get("Urls") or []
            Snipits = state.get("snippets", [])
            Title = state.get("titles", [])
            user_memory = MemoryManager.get_user_memory()

            FallBackResponse = self.FallBackResearch.invoke([
                SystemMessage(content=(
                    f"{DETAILED_RESEARCH_PROMPT}\n\n"
                    f"Plan:\n{plan}\n\n"
                    f"URLs:\n{Urls}\n\n"
                    f"Snippets:\n{Snipits}\n\n"
                    f"Titles:\n{Title}\n\n"
                    f"Memory:\n{user_memory}"
                )),
                HumanMessage(content=query)
            ])

            result = self.validate_response(FallBackResponse)
            usage = self.get_usage(FallBackResponse)

            return {
                "research_result": result,
                "model_used": [self.setting.fall_back_model],
                "error": None,
                "input_tokens": state.get("input_tokens", 0) + usage.get("input_tokens", 0),
                "output_tokens": state.get("output_tokens", 0) + usage.get("output_tokens", 0)
            }
        except Exception as e:
            return {"error": str(e)}

    def error_handler(self, state: StateClass) -> dict:
        return {
            "messages": [
                AIMessage(content="I ran into a problem while processing that request.")
            ],
            "error": state.get("error", "Unknown error")
        }

    @staticmethod
    def routing_after_processSEARCH(state: StateClass):
        if state.get("error") is None:
            return "done"
        if state.get("retry_countSimpleSearch", 0) < 2:
            return "fallback"
        return "error"

    @staticmethod
    def routing_after_fallbackSEARCH(state: StateClass):
        if state.get("error") is None:
            return "done"
        return "error"

    @staticmethod
    def routing_after_processRESEARCH(state: StateClass):
        if state.get("error") is None:
            return "done"
        if state.get("retry_countResearch", 0) < 2:
            return "fallback"
        return "error"

    @staticmethod
    def routing_after_fallbackRESEARCH(state: StateClass):
        if state.get("error") is None:
            return "done"
        return "error"

    @staticmethod
    def finishResearch(state: StateClass) -> dict:
        result = state.get("research_result")
        if result is None:
            return {
                "messages": [AIMessage(content="Research completed, but no structured result was returned.")]
            }
        return {
            "messages": [AIMessage(content=result.model_dump_json(indent=2))]
        }

    def builgGraph(self):
        graph = StateGraph(StateClass)

        graph.add_node("Memory", self.MakeMemory)
        graph.add_node("Plan", self.makePlan)
        graph.add_node("BaseSearch", self.makeBaseSearch)
        graph.add_node("UseFallBackSearch", self.UseFallBackSearch)
        graph.add_node("BaseResearch", self.makeBaseResearch)
        graph.add_node("makeFallResearch", self.makeFallResearch)
        graph.add_node("error_handler", self.error_handler)
        graph.add_node("finishResearch", self.finishResearch)

        graph.add_edge(START, "Memory")
        graph.add_edge("Memory", "Plan")
        graph.add_edge("Plan", "BaseSearch")

        graph.add_conditional_edges(
            "BaseSearch",
            self.routing_after_processSEARCH,
            {
                "done": "BaseResearch",
                "fallback": "UseFallBackSearch",
                "error": "error_handler"
            }
        )

        graph.add_conditional_edges(
            "UseFallBackSearch",
            self.routing_after_fallbackSEARCH,
            {
                "done": "BaseResearch",
                "error": "error_handler"
            }
        )

        graph.add_conditional_edges(
            "BaseResearch",
            self.routing_after_processRESEARCH,
            {
                "done": "finishResearch",
                "fallback": "makeFallResearch",
                "error": "error_handler"
            }
        )

        graph.add_conditional_edges(
            "makeFallResearch",
            self.routing_after_fallbackRESEARCH,
            {
                "done": "finishResearch",
                "error": "error_handler"
            }
        )

        graph.add_edge("finishResearch", END)
        graph.add_edge("error_handler", END)

        return graph.compile(store=memory, checkpointer=checkpointer)
    
    @traceable(name="Research Agent")
    def invoke(self, query: str, UserID: str) -> dict:
        result = self.graph.invoke(
            {
                "messages": [HumanMessage(content=query)],
                "Urls": [],
                "snippets": [],
                "titles": [],
                "planing": [],
                "memory": None,
                "research_result": None,
                "retry_countSimpleSearch": 0,
                "retry_countResearch": 0,
                "error": None,
                "model_used": [],
                "input_tokens": 0,
                "output_tokens": 0
            },
            config=MemoryManager.make_thread(user_id=UserID)
        )

        return {
            "research_result": result.get("research_result"),
            "error": result.get("error"),
            "model_used": result.get("model_used", []),
            "input_tokens": result.get("input_tokens", 0),
            "output_tokens": result.get("output_tokens", 0)
        }