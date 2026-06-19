/**
 * CodeGraph — shared TypeScript types.
 *
 * These types are the single source of truth consumed by:
 *   - js-analyzer/src/types.ts  (re-exports this file)
 *   - frontend/src/types/graph.ts (re-exports this file)
 *
 * They must stay in sync with schema/graph.schema.json.
 *
 * Node ID conventions (both analyzers MUST follow):
 *   file        →  "file:{rel/path}"               e.g. "file:src/app/page.tsx"
 *   table       →  "table:{TableName}"              e.g. "table:User"
 *   function    →  "fn:{rel/path}:{fnName}"         e.g. "fn:src/lib/auth.ts:getUser"
 *   component   →  "component:{rel/path}:{Name}"    e.g. "component:src/components/Button.tsx:Button"
 *   route       →  "route:{METHOD}:{path}"          e.g. "route:GET:/api/users"
 *   service     →  "service:{name}"                 e.g. "service:supabase"
 */

// ─── Enumerations ────────────────────────────────────────────────────────────

export type NodeType =
  | "table"      // DB table / ORM model
  | "file"       // source file
  | "function"   // plain function or class method
  | "component"  // React component
  | "route"      // HTTP route handler
  | "service";   // external service client (e.g. Supabase, Prisma client)

export type Language =
  | "python"
  | "typescript"
  | "javascript"
  | "sql"
  | "prisma"
  | "unknown";

export type EdgeKind =
  | "imports"   // file  → file        (import / require statement)
  | "calls"     // fn    → fn          (call site)
  | "reads"     // fn    → table       (SELECT / .findMany / .query)
  | "writes"    // fn    → table       (INSERT / UPDATE / DELETE / .create / .update)
  | "defines"   // file  → fn|component|route  (the file contains the definition)
  | "relation"; // table → table       (FK / @relation)

export type WarningKind =
  | "orphan_table"   // table has no read AND no write edges — likely dead weight
  | "unused_env_var" // DB env var declared but never referenced in code
  | "duplicate_table"; // two table nodes look like the same entity

export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE" | "HEAD" | "OPTIONS";

// ─── Sub-types ────────────────────────────────────────────────────────────────

export interface TableField {
  name: string;
  type: string;
  nullable?: boolean;
  isPrimaryKey?: boolean;
  isForeignKey?: boolean;
}

/** Node-type-specific extra data. Only populate the fields relevant to the node type. */
export interface NodeMeta {
  /** table nodes — column definitions */
  fields?: TableField[];
  /** function / component nodes — whether the symbol is exported */
  exported?: boolean;
  /** function nodes — parameter names in declaration order */
  params?: string[];
  /** route nodes — HTTP method */
  httpMethod?: HttpMethod;
  /** route nodes — URL path pattern, e.g. /api/users/[id] */
  routePath?: string;
}

// ─── Core graph types ─────────────────────────────────────────────────────────

export interface GraphNode {
  id: string;
  type: NodeType;
  name: string;       // short human-readable label (no path prefix)
  language: Language;
  /** Relative path from repo root. Empty string for schema-derived nodes (e.g. table inside schema.prisma). */
  file: string;
  /** 1-based line number where this node is defined, if known */
  line?: number;
  /** One-sentence plain-English description. Empty until M6 enrichment. */
  description?: string;
  meta?: NodeMeta;
}

export interface GraphEdge {
  source: string; // node id
  target: string; // node id
  kind: EdgeKind;
  /** 1-based line number of the reference in the source file, if known */
  line?: number;
}

export interface Warning {
  kind: WarningKind;
  message: string;
  /** The node this warning refers to, if applicable */
  nodeId?: string;
}

/** Top-level output emitted by each analyzer and consumed by the backend merger. */
export interface GraphResult {
  /** Source GitHub URL that was analyzed */
  repo?: string;
  /** Whole-graph plain-English summary. Empty until M6 enrichment. */
  summary?: string;
  /** Structural warnings. Populated by M6. */
  warnings?: Warning[];
  nodes: GraphNode[];
  edges: GraphEdge[];
}
