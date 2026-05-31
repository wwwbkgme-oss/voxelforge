# ADR-003: API-First Design with Local Python Fallback

**Date**: 2025-05-31
**Status**: Accepted

## Context

The `call_tool()` function in `forge/ai/tools.py` needs to execute generation
operations. It can either always use the HTTP API, always call Python directly,
or try HTTP first and fall back to Python.

## Decision

`call_tool()` tries the HTTP API first; if the server is not reachable
(ConnectionError, HTTPError, Timeout), it falls back to calling the Python
generators directly.

## Alternatives Considered

| Option | Pros | Cons | Why Rejected |
|--------|------|------|-------------|
| Always HTTP | Clean separation | Requires running server | Breaks offline use |
| Always Python | Works offline | Bypasses server (no asset dir sync) | Loses API benefits |
| **HTTP-first + fallback** | Best of both worlds | Slightly complex | Selected |

## Consequences

**Positive**:
- Agent and tools work offline with no server
- Full API features when server is running
- CI tests don't need a running server

**Negative**:
- Asset output dir differs between HTTP and local modes
- Must keep HTTP and local dispatch in sync

## Related ADRs
- ADR-002: Pure Python generators
