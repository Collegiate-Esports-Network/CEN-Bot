---
name: error-handling
description: Error handling conventions for CEN-Bot. Use this skill whenever writing or reviewing any code that makes database calls, API requests, or other fallible operations in CEN-Bot.
---

# Error Handling

## Pattern
All fallible operations use `try/except` with logging and a generic to the user, but sepecific to the operation, user-facing message:
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

## Logging
> **All fallible operations must have explicit error handling; never let exceptions propagate silently**

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

## User-Facing Messages
- Always send a generic message; never expose internal error details to users
- Always use `ephemeral=True` for error responses
- Always `return` after sending an error response to prevent further execution

## Exception Types
Handle the most specific exception type available:
- **Database calls:** `asyncpg.exceptions.PostgresError`
- **HTTP calls:** `aiohttp.ClientError`
- **All others:** `Exception` as a last resort