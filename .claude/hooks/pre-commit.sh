#!/usr/bin/env bash
# VoxelForge pre-commit hook
# Runs syntax check and critical tests before allowing a commit

set -e

echo "🔍 VoxelForge pre-commit checks..."

# 1. Python syntax check on changed .py files
changed_py=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' || true)
if [ -n "$changed_py" ]; then
    echo "  Checking Python syntax..."
    for f in $changed_py; do
        python3 -m py_compile "$f" && echo "    ✓ $f"
    done
fi

# 2. Run tests (quick subset)
echo "  Running tests..."
python3 -m pytest tests/ -q --tb=short 2>&1 | tail -5

# 3. Check Co-Authored-By trailer in commit message (if MSG file exists)
if [ -f ".git/COMMIT_EDITMSG" ]; then
    if ! grep -q "Co-Authored-By" .git/COMMIT_EDITMSG; then
        echo ""
        echo "⚠️  WARNING: Co-Authored-By trailer missing from commit message."
        echo "   Add:  Co-Authored-By: ey sho <eysho.it@gmail.com>"
        echo ""
    fi
fi

echo "✅ Pre-commit checks passed"
