---
status: created
created: "2026-03-11T22:00:00Z"
---
<summary>
- StatusCache exposes a public count method instead of leaking internal dict
- API endpoint no longer accesses private cache internals
</summary>

<objective>
Add a `count()` method to `StatusCache` and replace direct `cache._cache` access in `reload_cache()` to fix encapsulation violation.
</objective>

<context>
Read CLAUDE.md for project conventions.
Read `src/task_orchestrator/status_cache.py` — the `StatusCache` class.
Read `src/task_orchestrator/api/tasks.py` — the `reload_cache()` function (~line 511).

`reload_cache()` accesses `cache._cache.get(vault, {})` directly at ~lines 539 and 548 to get the count of cached items.
</context>

<requirements>
1. Add a `count()` method to `StatusCache`:
   ```python
   def count(self, vault_name: str) -> int:
       """Get number of cached items for a vault.

       Args:
           vault_name: Name of the vault

       Returns:
           Number of cached items, 0 if vault not loaded
       """
       return len(self._cache.get(vault_name, {}))
   ```

2. In `reload_cache()` in `tasks.py`, replace both occurrences of `len(cache._cache.get(..., {}))` with `cache.count(...)`:
   - ~line 539: `count = cache.count(vault)` (single vault reload)
   - ~line 548: `count = cache.count(vault_config.name)` (all vaults reload)
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git
- Existing tests must still pass
- Do NOT change the internal `_cache` data structure
</constraints>

<verification>
Run `make precommit` -- must pass.
</verification>
