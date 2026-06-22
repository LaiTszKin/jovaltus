# Core Package Architecture

## Module Boundary: Tools

The tools module owns tool registration, discovery, execution, and session-level read tracking. It does not own agent loop orchestration or context composition.

**Evidence**: `packages/core/src/tools/` — `types.ts`, `registry.ts`, `read-state.ts`, `workspace.ts`, `read-tool.ts`, `write-tool.ts`, `edit-tool.ts`, `bash-tool.ts`

### Tool Registry as Central Catalog

The `ToolRegistry` interface (`packages/core/src/tools/types.ts:83-105`) is the single point of tool discovery and execution for the runtime. It enforces:

- No duplicate id or name on registration (pre-registration check before indexing)
- Id-based lookup (`get(id)`) and name-based lookup (`getByName(name)`)
- Structured execution via `execute()` that catches handler exceptions and returns `ToolResult` objects instead of throwing

### Workspace Path Containment

File tools resolve user-supplied paths against `context.workspaceRoot` and reject targets that escape the workspace boundary. The shared helper `resolveInWorkspace` in `workspace.ts:39-135` (`async`, returns `Promise<WorkspaceResult>`) rejects out-of-bound paths through three layers of containment checking:

1. **Lexical containment** — a fast check that rejects obvious `../` traversal and absolute-outside paths with zero filesystem access.
2. **Canonical containment** — for existing targets, `fs.realpath` resolves all symlinks and the canonical path is checked against the canonical workspace root. This catches `link-to-outside/secret.txt` where the symlink points outside.
3. **Parent-walk containment** — for non-existing targets (new file writes), walks up the directory tree to find the nearest existing ancestor, resolves symlinks via `realpath`, and verifies containment.

All three layers return `INVALID_PARAMS` before any filesystem I/O occurs.

- **Read tool**: containment check at `read-tool.ts:42-44` (`await resolveInWorkspace`), before read-state update and file I/O.
- **Write tool**: containment check at `write-tool.ts:69-71` (`await resolveInWorkspace`), before read-before-write guard and file creation.
- **Edit tool**: containment check at `edit-tool.ts:63-65` (`await resolveInWorkspace`), before read-before-write guard.

Valid in-workspace absolute paths are accepted as long as they resolve inside `workspaceRoot`. Paths whose first segment begins with `..` but is not a parent traversal (e.g. `..foo/file.txt`) are preserved.

### Read-Before-Write Safety

The `ReadState` interface (`packages/core/src/tools/read-state.ts:7-19`) tracks per-session file reads. It uses path normalization (`resolvePath` + trailing-slash dedup) so the same file is recognized regardless of how the path was spelled. Read tool writes to `ReadState` only after a successful read; write and edit tools check `ReadState` before modifying existing files.

### Structured Error Contract

Every tool result is typed as `ToolResult` (`packages/core/src/tools/types.ts:28-32`) with `success`, optional `data`, and optional `error` containing a `ToolErrorCode` and message. The registry guarantees no exceptions escape `execute()` — unknown tools return `TOOL_NOT_FOUND`, handler exceptions are caught and returned as `UNKNOWN_ERROR`.

## Module Boundary: Context

The context module owns composing a single-agent context bundle from providers. It does not own memory persistence, skill marketplaces, or MCP server execution.

**Evidence**: `packages/core/src/context/` — `types.ts`, `composer.ts`

### Provider-Based Composition

`ContextProvider<T>` (`packages/core/src/context/types.ts:7-11`) is the abstraction for supplying a section of agent context. The composer accepts optional custom providers and falls back to default providers that return `null` (memory, skills, MCP) or empty tool lists.

### Graceful Optional Provider Degradation

Optional providers (memory, skills, MCP) are wrapped in a `safeGet` helper (`composer.ts:104-112`) that catches rejections and returns `null`. This prevents a single failing optional provider from blocking the entire context composition. The tool provider is never wrapped — its rejections propagate as mandatory failures.

### Narrow Tool Registry Type

The composer defines a `ToolRegistryItem` interface (`types.ts:72-79`) with only the fields it needs from the tool catalog: `definition` (id, name, description) and `parameters`. The `ContextComposerOptions.toolRegistry` (`types.ts:81-84`) accepts a `list()` method returning `readonly ToolRegistryItem[]`, replacing an earlier `any[]` type.

### Tools-as-Metadata-Only

When the composer generates tool descriptions (`packages/core/src/context/composer.ts:47-67`), it reads only `definition` and `parameters` from registered tools. It never calls `handler`. This ensures context composition is side-effect-free.

## Data Flow

```
Runtime ──► ToolRegistry ──► execute(id, params, context) ──► ToolResult
                │               │
                │               ├── resolveInWorkspace() ──► workspace.ts:39-135
                │               │      INVALID_PARAMS (lexical / realpath / parent-walk)
                │               │      resolved path (string) if valid
                │               │
                │               ├── (read|write|edit) handler
                │               └── ToolResult
                │
                ├── get(id)        ──► Tool | undefined
                ├── getByName(name) ──► Tool | undefined
                └── list()         ──► Tool[]

Runtime ──► ContextComposer ──► compose(options) ──► AgentContext
                │
                ├── memory provider ──► safeGet() ──► MemoryContext | null
                ├── skills provider ──► safeGet() ──► SkillsContext | null
                ├── tools provider   ──► (mandatory) ToolDescriptions
                └── MCP provider     ──► safeGet() ──► MCPContext | null
```

## Boundary Invariants

- Tool modules do not call context modules or agent loop logic
- Context modules read from ToolRegistry but never execute handlers
- ReadState is per-session; no cross-session sharing
- File tools reject any path whose resolved target is outside `context.workspaceRoot` with `INVALID_PARAMS` before filesystem access
- All public types are exported from `packages/core/src/index.ts`
