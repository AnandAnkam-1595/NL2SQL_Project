import os
import uuid
import traceback
import sqlite3
import json
import math
import pandas as pd
import plotly.express as px
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from vanna_setup import agent, memory, llm, schema
from vanna.core.user import RequestContext, User

app = FastAPI(title="NL2SQL Clinic API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Query(BaseModel):
    question: str

    @validator("question")
    def validate_question(cls, v):
        if not v or not v.strip():
            raise ValueError("Question cannot be empty")
        if len(v) > 500:
            raise ValueError("Question too long (max 500 chars)")
        return v.strip()


def sanitize(obj):
    """Recursively sanitize NaN/Infinity values for JSON compliance."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize(i) for i in obj]
    return obj


def validate_sql(sql: str) -> tuple[bool, str]:
    if not sql:
        return False, "Empty SQL"
    sql_lower = sql.lower().strip()
    if not sql_lower.startswith("select"):
        return False, "Only SELECT queries are allowed"
    banned = ["insert", "update", "delete", "drop", "alter",
              "exec", "xp_", "sp_", "grant", "revoke", "shutdown"]
    for word in banned:
        if word in sql_lower:
            return False, f"Forbidden keyword: {word}"
    if "sqlite_master" in sql_lower or "sqlite_sequence" in sql_lower:
        return False, "Access to system tables not allowed"
    return True, "ok"


def extract_sql_from_text(text: str) -> str:
    import re
    match = re.search(r"```(?:sql)?\s*(SELECT.*?)```", text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r"(SELECT\s+.+?)(?:;|\Z)", text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def extract_from_chunks(chunks):
    sql = ""
    data = []
    message = ""
    columns = []
    for chunk in chunks:
        rc = getattr(chunk, "rich_component", None)
        sc = getattr(chunk, "simple_component", None)
        if rc is not None:
            rc_type = type(rc).__name__
            if rc_type in ["StatusBarUpdateComponent", "TaskTrackerUpdateComponent",
                           "ChatInputUpdateComponent"]:
                continue
            if not sql and hasattr(rc, "sql") and rc.sql:
                sql = rc.sql
            if not data and hasattr(rc, "df") and rc.df is not None:
                try:
                    columns = list(rc.df.columns)
                    data = rc.df.values.tolist()
                except Exception:
                    pass
            if hasattr(rc, "children") and rc.children:
                for child in rc.children:
                    if not sql and hasattr(child, "sql") and child.sql:
                        sql = child.sql
                    if not data and hasattr(child, "df") and child.df is not None:
                        try:
                            columns = list(child.df.columns)
                            data = child.df.values.tolist()
                        except Exception:
                            pass
        if sc is not None:
            if hasattr(sc, "text") and sc.text:
                text = sc.text
                if "Error" not in text and "Try again" not in text:
                    message = text
    return sql, columns, data, message


def get_sql_from_llm(question: str) -> str:
    try:
        prompt = f"""You are a SQLite expert. Write a SELECT query to answer this question.
Return ONLY the SQL query with no explanation, no markdown, no backticks.

Schema:
{schema}

Question: {question}

SQL:"""
        response = llm._client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300
        )
        raw = response.choices[0].message.content.strip()
        sql = extract_sql_from_text(raw)
        return sql if sql else raw
    except Exception as e:
        print(f"LLM SQL generation error: {e}")
        return ""


def execute_sql(sql: str):
    conn = sqlite3.connect("clinic.db")
    df = pd.read_sql_query(sql, conn)
    conn.close()
    # Replace NaN with None
    df = df.where(pd.notnull(df), None)
    return list(df.columns), df.values.tolist(), df


def generate_chart(df: pd.DataFrame, question: str):
    try:
        if df.empty or len(df.columns) < 2:
            return None, None
        num_cols = df.select_dtypes(include="number").columns.tolist()
        str_cols = df.select_dtypes(exclude="number").columns.tolist()
        if not num_cols:
            return None, None
        x_col = str_cols[0] if str_cols else df.columns[0]
        y_col = num_cols[0]
        q_lower = question.lower()
        if any(w in q_lower for w in ["trend", "month", "over time", "monthly"]):
            fig = px.line(df, x=x_col, y=y_col, title=question)
            chart_type = "line"
        else:
            fig = px.bar(df, x=x_col, y=y_col, title=question)
            chart_type = "bar"
        # ✅ Use plotly's JSON serializer to avoid float issues
        chart_json = json.loads(fig.to_json())
        return chart_json, chart_type
    except Exception:
        return None, None


def make_response(data: dict):
    """Return JSONResponse with sanitized data."""
    return JSONResponse(content=sanitize(data))


@app.post("/chat")
async def chat(q: Query):
    try:
        # Step 1: Try agent first
        sql = ""
        columns = []
        rows = []
        message = ""

        try:
            ctx = RequestContext(
                user=User(
                    id="admin",
                    email="admin@clinic.com",
                    group_memberships=["admin", "user"]
                ),
                conversation_id=str(uuid.uuid4()),
                request_id=str(uuid.uuid4()),
            )
            stream = agent.send_message(
                message=q.question,
                request_context=ctx
            )
            chunks = []
            async for chunk in stream:
                chunks.append(chunk)
            sql, columns, rows, message = extract_from_chunks(chunks)
        except Exception as agent_err:
            print(f"Agent error (will fallback to direct LLM): {agent_err}")

        # Step 2: Fallback to direct LLM if no SQL
        if not sql:
            sql = get_sql_from_llm(q.question)

        if not sql:
            return make_response({
                "message": message or "Could not generate SQL for this question.",
                "sql_query": "",
                "columns": [],
                "rows": [],
                "row_count": 0,
                "chart": None,
                "chart_type": None
            })

        # Step 3: Validate SQL
        valid, reason = validate_sql(sql)
        if not valid:
            return make_response({
                "message": f"SQL validation failed: {reason}",
                "sql_query": sql,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "chart": None,
                "chart_type": None
            })

        # Step 4: Execute if no data from agent
        df_result = None
        if not rows:
            try:
                columns, rows, df_result = execute_sql(sql)
            except Exception as e:
                return make_response({
                    "message": f"Query execution failed: {str(e)}",
                    "sql_query": sql,
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "chart": None,
                    "chart_type": None
                })

        if not rows:
            return make_response({
                "message": "No data found for this query.",
                "sql_query": sql,
                "columns": columns,
                "rows": [],
                "row_count": 0,
                "chart": None,
                "chart_type": None
            })

        # Step 5: Generate chart
        if df_result is None:
            df_result = pd.DataFrame(rows, columns=columns) if columns else pd.DataFrame(rows)
        chart, chart_type = generate_chart(df_result, q.question)

        return make_response({
            "message": message or f"Found {len(rows)} result(s).",
            "sql_query": sql,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "chart": chart,
            "chart_type": chart_type
        })

    except Exception as e:
        traceback.print_exc()
        return make_response({
            "message": f"Error: {str(e)}",
            "sql_query": "",
            "columns": [],
            "rows": [],
            "row_count": 0,
            "chart": None,
            "chart_type": None
        })


@app.get("/health")
async def health():
    try:
        conn = sqlite3.connect("clinic.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM patients")
        conn.close()
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return JSONResponse(content={
        "status": "ok",
        "database": db_status,
        "agent_memory_items": 15
    })