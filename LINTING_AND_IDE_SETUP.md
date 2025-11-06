# Linting and IDE Setup

This document explains the linting configuration and how to handle common IDE warnings.

## Optional Dependencies and IDE Warnings

### The OpenAI Import Issue

**Problem:** IDEs show red underlines for `import openai` with error:
- "Import 'openai' could not be resolved"
- "OpenAI SDK imported without Guardrails"

**Root Cause:** The `openai` package is an **optional dependency**:
- Not needed for POC (uses free Ollama)
- Only needed for production (uses paid OpenAI API)
- Installed on-demand: `pip install openai`

### Solution Implemented

1. **Type Checker Fix** - Added type ignore comment:
   ```python
   import openai  # type: ignore[import-not-found]
   ```

2. **Codacy/Semgrep Config** - Disabled the guardrails rule in `.codacy/codacy.yaml`:
   ```yaml
   - semgrep@1.78.0:
       exclude_rules:
         - codacy.python.openai.import-without-guardrails
   ```

3. **Documentation** - Created `OPTIONAL_DEPENDENCIES.md` explaining the pattern

## Linting Tools Used

### 1. Codacy (CI/CD)

Configuration: `.codacy/codacy.yaml`

Tools enabled:
- **Semgrep** - Security and best practices
- **Pylint** - Python code quality
- **ESLint** - JavaScript (if present)
- Others: dartanalyzer, lizard, pmd, revive, trivy

### 2. Pylance/Pyright (IDE)

VS Code's built-in Python type checker.

**Configuration:** Uses inline `# type: ignore` comments for optional imports.

### 3. Local Linting (Optional)

Not currently configured, but you can add:

```bash
# Install linting tools
pip install pylint black flake8 mypy

# Run locally
pylint src/
black src/
flake8 src/
mypy src/
```

## Common Warnings and How to Handle Them

### 1. "Import could not be resolved"

**Cause:** Optional dependency not installed

**Fix:**
- If it's optional (like `openai`): Add `# type: ignore[import-not-found]`
- If it's required: Install the package

**Example:**
```python
import openai  # type: ignore[import-not-found]
```

### 2. "Variable/import not accessed"

**Cause:** Import only used at runtime

**Fix:** Use `TYPE_CHECKING` pattern or ignore:
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import optional_package
```

### 3. "Security: Use Guardrails for OpenAI"

**Cause:** Semgrep security rule

**Context:** Guardrails is a security wrapper for LLM calls, but:
- Not needed for embedding-only usage
- Not needed for POC/development
- Optional security enhancement for production

**Fix:**
- Excluded in Codacy config for this project
- Consider adding for production with user-facing LLM features

### 4. "Missing type annotations"

**Cause:** Pylint/mypy wants type hints

**Fix:** Add type hints:
```python
def my_function(text: str) -> List[float]:
    ...
```

## IDE-Specific Setup

### VS Code

**settings.json:**
```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.diagnosticSeverityOverrides": {
    "reportMissingImports": "none",
    "reportOptionalMemberAccess": "none"
  }
}
```

### PyCharm

1. Settings → Editor → Inspections
2. Python → Unresolved references → Configure
3. Add `openai` to ignored imports for optional dependencies

## Suppressing Warnings

### Inline Suppression

```python
# Pylance/mypy
import optional  # type: ignore[import-not-found]

# Multiple checkers
import optional  # type: ignore  # noqa: F401

# Specific line
result = risky_call()  # nosec

# Block
# pylint: disable=import-error
import optional_package
# pylint: enable=import-error
```

### File-Level Suppression

```python
# At top of file
# pylint: disable=import-error,missing-docstring
```

### Config-Level Suppression

See `.codacy/codacy.yaml` for examples.

## Best Practices

### 1. Optional Dependencies

✅ **DO:**
- Use lazy imports (import inside function/class)
- Add type ignore comments
- Handle ImportError gracefully
- Document in requirements.txt as optional

❌ **DON'T:**
- Import at module level if optional
- Hide errors without explanation
- Require optional deps for core features

### 2. Type Checking

✅ **DO:**
- Add type hints to public APIs
- Use `TYPE_CHECKING` for circular imports
- Ignore warnings for valid patterns

❌ **DON'T:**
- Over-suppress (hide real errors)
- Ignore type checking entirely
- Add types everywhere (focus on interfaces)

### 3. Security Warnings

✅ **DO:**
- Understand the warning
- Document why it's safe to ignore
- Add to config if project-wide decision

❌ **DON'T:**
- Ignore without understanding
- Disable all security checks
- Suppress without comments

## Project-Specific Decisions

### OpenAI + Guardrails

**Decision:** Not using Guardrails

**Rationale:**
1. POC → Production migration pattern
2. Ollama (default) doesn't need Guardrails
3. Embedding-only usage (no user input to LLM)
4. Optional production enhancement

**Documented in:**
- `OPTIONAL_DEPENDENCIES.md`
- `.codacy/codacy.yaml`
- This file

### Type Checking Level

**Decision:** Basic type checking

**Rationale:**
1. Balance between safety and flexibility
2. Allows optional dependencies
3. Focuses on public APIs
4. Doesn't slow development

## Updating Configuration

### Add New Optional Dependency

1. Add to `requirements.txt` as comment:
   ```
   # optional_pkg==1.0.0  # Uncomment for feature X
   ```

2. Use lazy import with type ignore:
   ```python
   try:
       import optional_pkg  # type: ignore[import-not-found]
   except ImportError:
       raise ImportError("Install with: pip install optional_pkg")
   ```

3. Document in `OPTIONAL_DEPENDENCIES.md`

### Disable New Linting Rule

1. **If false positive:** Add to `.codacy/codacy.yaml`:
   ```yaml
   - semgrep@1.78.0:
       exclude_rules:
         - rule.name.here
   ```

2. **If valid but not applicable:** Document why in code comment

3. **If needs fixing:** Create issue/TODO

## Troubleshooting

### "Import error persists after installing package"

Reload VS Code:
1. Cmd+Shift+P
2. "Developer: Reload Window"

Or restart Python language server:
1. Cmd+Shift+P
2. "Python: Restart Language Server"

### "Codacy still shows error after config change"

- Config only affects new Codacy runs (CI/CD)
- Local IDE may still show warning
- IDE warnings are from Pylance, not Codacy

### "Too many warnings to fix"

Priorities:
1. **Fix:** Real errors and security issues
2. **Document:** Valid patterns that look wrong
3. **Suppress:** False positives
4. **Ignore:** Low-priority style issues

## References

- **Codacy Docs**: https://docs.codacy.com/
- **Pylance**: https://github.com/microsoft/pylance-release
- **Semgrep**: https://semgrep.dev/
- **Type Checking**: https://typing.readthedocs.io/

---

**Questions?** Check if warning is about:
1. Optional dependency → See `OPTIONAL_DEPENDENCIES.md`
2. Security → Evaluate if applicable to your use case
3. Style → Consider fixing or suppressing based on project standards
