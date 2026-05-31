# ADR-004: Lua Script Templates Use String Concatenation (Not f-strings)

**Date**: 2025-05-31
**Status**: Accepted

## Context

Lua uses `{}` for table literals (e.g., `local dirs = {1,0,-1,0}`).
Python f-strings and `.format()` both use `{}` as delimiters.
This creates a conflict when embedding Lua table syntax in Python string templates.

Python 3.12+ raises `SyntaxError` for f-strings with unbalanced braces,
and `.format()` raises `ValueError: Single '}' encountered`.

## Decision

All Lua script templates in `forge/generators/game.py` use plain string
concatenation to inject variables, and Lua's `{}` table literals are
always embedded via concatenation with plain `"{"` / `"}"` string literals.

## Alternatives Considered

| Option | Pros | Cons | Why Rejected |
|--------|------|------|-------------|
| f-strings | Readable | SyntaxError in Python 3.12+ | Rejected |
| `.format()` | Familiar | ValueError on bare `}` | Rejected |
| Jinja2 templates | Powerful | Extra dependency | Deferred |
| `string.Template` ($-style) | No conflict | Less readable | Could work |
| **String concatenation** | No conflict, no deps | Verbose | Selected |

## Consequences

**Positive**:
- Works on all Python 3.10+ versions
- No extra dependencies
- Easy to audit what Lua code is generated

**Negative**:
- Lua templates are verbose and hard to read
- Can't use modern IDE Lua syntax highlighting in templates

## Example

```python
# CORRECT:
template = "local dirs = " + "{1,0},{-1,0},{0,1},{0,-1}" + "\n"

# WRONG:
template = f"local dirs = {1,0},{-1,0},{0,1},{0,-1}\n"  # SyntaxError
```
