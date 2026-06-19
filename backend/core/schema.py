"""
Python-side graph types — mirror of schema/graph.types.ts.
Uses Pydantic so FastAPI can serialize/validate them directly.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class NodeType(str, Enum):
    TABLE = "table"
    FILE = "file"
    FUNCTION = "function"
    COMPONENT = "component"
    ROUTE = "route"
    SERVICE = "service"


class Language(str, Enum):
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    SQL = "sql"
    PRISMA = "prisma"
    UNKNOWN = "unknown"


class EdgeKind(str, Enum):
    IMPORTS = "imports"
    CALLS = "calls"
    READS = "reads"
    WRITES = "writes"
    DEFINES = "defines"
    RELATION = "relation"


class WarningKind(str, Enum):
    ORPHAN_TABLE = "orphan_table"
    UNUSED_ENV_VAR = "unused_env_var"
    DUPLICATE_TABLE = "duplicate_table"


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class TableField(BaseModel):
    name: str
    type: str
    nullable: bool = False
    isPrimaryKey: bool = False
    isForeignKey: bool = False


class NodeMeta(BaseModel):
    fields: list[TableField] = []
    exported: Optional[bool] = None
    params: list[str] = []
    httpMethod: Optional[HttpMethod] = None
    routePath: Optional[str] = None


class GraphNode(BaseModel):
    id: str
    type: NodeType
    name: str
    language: Language
    file: str
    line: Optional[int] = None
    description: Optional[str] = None
    meta: Optional[NodeMeta] = None


class GraphEdge(BaseModel):
    source: str
    target: str
    kind: EdgeKind
    line: Optional[int] = None


class Warning(BaseModel):
    kind: WarningKind
    message: str
    nodeId: Optional[str] = None


class GraphResult(BaseModel):
    repo: Optional[str] = None
    summary: Optional[str] = None
    warnings: list[Warning] = []
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
