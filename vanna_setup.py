import os
from dotenv import load_dotenv
from vanna import Agent, AgentConfig
from vanna.core.registry import ToolRegistry
from vanna.core.user import UserResolver, User, RequestContext
from vanna.tools import RunSqlTool, VisualizeDataTool
from vanna.tools.agent_memory import SaveQuestionToolArgsTool, SearchSavedCorrectToolUsesTool
from vanna.integrations.sqlite import SqliteRunner
from vanna.integrations.local.agent_memory import DemoAgentMemory
from vanna.integrations.openai import OpenAILlmService
import sqlite3

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# LLM - Groq via OpenAI-compatible API
llm = OpenAILlmService(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY,
    model="llama-3.3-70b-versatile"
)

# Database
sql_runner = SqliteRunner(database_path="clinic.db")
db_tool = RunSqlTool(sql_runner=sql_runner)

# Memory
memory = DemoAgentMemory(max_items=1000)

# Get schema for system prompt
def get_schema():
    conn = sqlite3.connect("clinic.db")
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    conn.close()
    return "\n\n".join([t[0] for t in tables if t[0]])

schema = get_schema()

SYSTEM_PROMPT = f"""You are an expert SQL assistant for a clinic management system.
You MUST ALWAYS use the RunSqlTool to answer ANY question. Never answer from memory.
Always execute a SQL query even if you think you know the answer.

Database Schema:
{schema}

Rules:
- ALWAYS call RunSqlTool with a SELECT query - this is MANDATORY
- Never respond with text only - always run a SQL query first
- Only use SELECT statements, never INSERT/UPDATE/DELETE/DROP
- Use exact table and column names from the schema above
- For date filtering use SQLite functions: date('now', '-30 days')
- After getting results, provide a clear summary
"""

# Tool Registry
tools = ToolRegistry()
tools.register_local_tool(db_tool, access_groups=["admin", "user"])
tools.register_local_tool(VisualizeDataTool(), access_groups=["admin", "user"])
tools.register_local_tool(SaveQuestionToolArgsTool(), access_groups=["admin"])
tools.register_local_tool(SearchSavedCorrectToolUsesTool(), access_groups=["admin", "user"])

# User Resolver
class DefaultUserResolver(UserResolver):
    async def resolve_user(self, ctx: RequestContext):
        return User(
            id="default",
            email="default@clinic.com",
            group_memberships=["admin", "user"]
        )

# Agent
agent = Agent(
    config=AgentConfig(system_prompt=SYSTEM_PROMPT),
    llm_service=llm,
    tool_registry=tools,
    agent_memory=memory,
    user_resolver=DefaultUserResolver()
)