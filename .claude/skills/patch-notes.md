# /patch-notes — Generate Patch Notes / Changelog

**Usage**: `/patch-notes [version]`

**Description**: Generate formatted patch notes from recent git commits.

## Process

```bash
# Get recent commits
git log --oneline -20

# Format into changelog sections:
# feat: → ✨ New Features
# fix:  → 🐛 Bug Fixes
# perf: → ⚡ Performance
# docs: → 📚 Documentation
# test: → 🧪 Testing
# refactor: → ♻️ Refactoring
```

## Output Template

```markdown
# VoxelForge vX.Y.Z — Patch Notes

*Released: <date>*

## ✨ New Features

- **<Feature>**: <description> (`<endpoint or module>`)

## 🐛 Bug Fixes

- Fixed <issue> in `<module>` — <what was wrong, what was fixed>

## ⚡ Performance

- <improvement>

## 📚 Documentation

- Updated README with <section>

## 🧪 Testing

- Added N tests for <feature>
- All N tests passing

## 🔧 Breaking Changes

- `<function_name>` parameter `radius` renamed to `range_` (matches engine JSON)

## Upgrade Guide

```python
# Before
scene.add_point_light("sun", radius=100)

# After
scene.add_point_light("sun", range_=100)
```
```
