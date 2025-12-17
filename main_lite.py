"""Superset MCP Lite - Versão otimizada com menos ferramentas e docstrings curtas para economizar tokens."""

from typing import Any, Dict, List, Optional, AsyncIterator, Callable, Awaitable
import os
import httpx
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import wraps
from mcp.server.fastmcp import FastMCP, Context
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

SUPERSET_BASE_URL = os.getenv("SUPERSET_BASE_URL", "http://localhost:8088")
SUPERSET_USERNAME = os.getenv("SUPERSET_USERNAME")
SUPERSET_PASSWORD = os.getenv("SUPERSET_PASSWORD")
ACCESS_TOKEN_STORE_PATH = os.path.join(os.path.dirname(__file__), ".superset_token")


@dataclass
class SupersetContext:
    client: httpx.AsyncClient
    base_url: str
    access_token: Optional[str] = None
    csrf_token: Optional[str] = None


def load_stored_token() -> Optional[str]:
    try:
        if os.path.exists(ACCESS_TOKEN_STORE_PATH):
            with open(ACCESS_TOKEN_STORE_PATH, "r") as f:
                return f.read().strip()
    except Exception:
        pass
    return None


def save_access_token(token: str):
    try:
        with open(ACCESS_TOKEN_STORE_PATH, "w") as f:
            f.write(token)
    except Exception as e:
        logger.warning(f"Could not save token: {e}")


@asynccontextmanager
async def superset_lifespan(server: FastMCP) -> AsyncIterator[SupersetContext]:
    client = httpx.AsyncClient(base_url=SUPERSET_BASE_URL, timeout=30.0)
    ctx = SupersetContext(client=client, base_url=SUPERSET_BASE_URL)

    stored_token = load_stored_token()
    if stored_token:
        ctx.access_token = stored_token
        client.headers.update({"Authorization": f"Bearer {stored_token}"})
        try:
            response = await client.get("/api/v1/me/")
            if response.status_code != 200:
                ctx.access_token = None
                client.headers.pop("Authorization", None)
        except Exception:
            ctx.access_token = None
            client.headers.pop("Authorization", None)

    try:
        yield ctx
    finally:
        await client.aclose()


mcp = FastMCP("superset-lite", lifespan=superset_lifespan)


def requires_auth(func):
    @wraps(func)
    async def wrapper(ctx: Context, *args, **kwargs):
        superset_ctx: SupersetContext = ctx.request_context.lifespan_context
        if not superset_ctx.access_token:
            return {"error": "Not authenticated"}
        return await func(ctx, *args, **kwargs)
    return wrapper


async def get_csrf_token(ctx: Context) -> Optional[str]:
    superset_ctx: SupersetContext = ctx.request_context.lifespan_context
    try:
        response = await superset_ctx.client.get("/api/v1/security/csrf_token/")
        if response.status_code == 200:
            csrf = response.json().get("result")
            superset_ctx.csrf_token = csrf
            return csrf
    except Exception:
        pass
    return None


async def api_request(ctx: Context, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
    superset_ctx: SupersetContext = ctx.request_context.lifespan_context
    client = superset_ctx.client

    if method.lower() != "get" and not superset_ctx.csrf_token:
        await get_csrf_token(ctx)

    headers = {}
    if method.lower() != "get":
        if superset_ctx.csrf_token:
            headers["X-CSRFToken"] = superset_ctx.csrf_token
        headers["Referer"] = superset_ctx.base_url

    try:
        if method.lower() == "get":
            response = await client.get(endpoint, params=params)
        elif method.lower() == "post":
            response = await client.post(endpoint, json=data, params=params, headers=headers)
        else:
            return {"error": f"Method {method} not supported"}

        if response.status_code not in [200, 201]:
            return {"error": f"{response.status_code} - {response.text}"}
        return response.json()
    except Exception as e:
        return {"error": str(e)}


# ===== FERRAMENTAS ESSENCIAIS (10 ferramentas vs 61 originais) =====

@mcp.tool()
async def superset_login(ctx: Context, username: str = None, password: str = None) -> Dict[str, Any]:
    """Autentica no Superset. Usa env vars se credenciais não fornecidas."""
    superset_ctx: SupersetContext = ctx.request_context.lifespan_context

    if superset_ctx.access_token:
        try:
            response = await superset_ctx.client.get("/api/v1/me/")
            if response.status_code == 200:
                return {"message": "Already authenticated"}
        except Exception:
            pass

    username = username or SUPERSET_USERNAME
    password = password or SUPERSET_PASSWORD

    if not username or not password:
        return {"error": "Credentials required"}

    try:
        response = await superset_ctx.client.post(
            "/api/v1/security/login",
            json={"username": username, "password": password, "provider": "db", "refresh": True},
        )
        if response.status_code != 200:
            return {"error": f"Login failed: {response.status_code}"}

        token = response.json().get("access_token")
        if not token:
            return {"error": "No token returned"}

        save_access_token(token)
        superset_ctx.access_token = token
        superset_ctx.client.headers.update({"Authorization": f"Bearer {token}"})
        await get_csrf_token(ctx)
        return {"message": "Authenticated successfully"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
@requires_auth
async def superset_databases(ctx: Context) -> Dict[str, Any]:
    """Lista databases disponíveis."""
    return await api_request(ctx, "get", "/api/v1/database/")


@mcp.tool()
@requires_auth
async def superset_tables(ctx: Context, database_id: int) -> Dict[str, Any]:
    """Lista tabelas de um database."""
    return await api_request(ctx, "get", f"/api/v1/database/{database_id}/tables/")


@mcp.tool()
@requires_auth
async def superset_schemas(ctx: Context, database_id: int) -> Dict[str, Any]:
    """Lista schemas de um database."""
    return await api_request(ctx, "get", f"/api/v1/database/{database_id}/schemas/")


@mcp.tool()
@requires_auth
async def superset_query(ctx: Context, database_id: int, sql: str) -> Dict[str, Any]:
    """Executa query SQL e retorna resultados."""
    superset_ctx: SupersetContext = ctx.request_context.lifespan_context
    if not superset_ctx.csrf_token:
        await get_csrf_token(ctx)

    payload = {
        "database_id": database_id,
        "sql": sql,
        "schema": "",
        "tab": "MCP",
        "runAsync": False,
        "select_as_cta": False,
    }
    return await api_request(ctx, "post", "/api/v1/sqllab/execute/", data=payload)


@mcp.tool()
@requires_auth
async def superset_datasets(ctx: Context) -> Dict[str, Any]:
    """Lista datasets disponíveis."""
    return await api_request(ctx, "get", "/api/v1/dataset/")


@mcp.tool()
@requires_auth
async def superset_dataset(ctx: Context, dataset_id: int) -> Dict[str, Any]:
    """Detalhes de um dataset (colunas, métricas)."""
    return await api_request(ctx, "get", f"/api/v1/dataset/{dataset_id}")


@mcp.tool()
@requires_auth
async def superset_dashboards(ctx: Context) -> Dict[str, Any]:
    """Lista dashboards."""
    return await api_request(ctx, "get", "/api/v1/dashboard/")


@mcp.tool()
@requires_auth
async def superset_charts(ctx: Context) -> Dict[str, Any]:
    """Lista charts."""
    return await api_request(ctx, "get", "/api/v1/chart/")


@mcp.tool()
async def superset_url(ctx: Context) -> Dict[str, Any]:
    """Retorna URL base do Superset."""
    superset_ctx: SupersetContext = ctx.request_context.lifespan_context
    return {"base_url": superset_ctx.base_url}


if __name__ == "__main__":
    logger.info("Starting Superset MCP Lite...")
    mcp.run()
