---
name: error-handling
description: Use when working on fallible operations in CEN-Bot, especially database or HTTP code, so exceptions, logging, and user-facing failure messages follow repo conventions.
---

# Error Handling
> **All fallible operations must have explicit error handling; never let exceptions propagate silently**

- Always let the user know an error has occurred.
- Always send a generic message; never expose internal error details to users.
- Always use `ephemeral=True` for error responses.
- Always `return` after sending an error response to prevent further execution.
```python
try:
    async with self.bot.db_pool.acquire() as conn:
        await conn.execute("""...""", ...)
except PostgresError as e:
    log.exception(e)
    await interaction.response.send_message(
        "There was an error saving your data, please try again.",
        ephemeral=True
    )
    return
```

## Exception Types
- Always handle the most specific exception type available:
  - **Database calls:** `asyncpg.exceptions.PostgresError`
  - **HTTP calls:** `aiohttp.ClientError`
- The generic `Exception` should only be used as a last resort.

## Logging
- `log.error(f"...")`: use for known error conditions where you control the message and a traceback isn't needed
- `log.exception(e)`: use for caught exceptions where the traceback is useful
  - Ex: DB errors, API failures, anything unexpected
- `log.info(f"...")`: use for expected successful operations that are useful to log
  - Ex: user actions, successful API calls
- `log.debug(f"...")`: use for verbose debugging information that isn't normally needed
  - Ex: detailed API responses, internal state changes
- `log.warning(f"...")`: use for recoverable issues that aren't necessarily errors but may warrant attention
  - Ex: rate limit warnings, deprecated API usage

```python
# Exception; traceback needed
except PostgresError as e:
    log.exception(e)

# Known condition; traceback not needed
if resp.status != 200:
    log.error(f"Twitch API returned {resp.status} for query: {query!r}")
```
