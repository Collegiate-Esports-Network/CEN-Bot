"""Supabase Realtime helpers for cross-process registration handoffs."""

__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = ["Justin Panchula", "Claude"]
__version__ = "0.1.0"
__status__ = "Development"

# Standard library
import asyncio
from logging import getLogger
from typing import Any, Awaitable, Callable

# Third-party
from supabase import AsyncClient

log = getLogger('CENBot.realtime')

# Type alias for the async callback fired when a watched registration completes
RegistrationCallback = Callable[[int], Awaitable[None]]


class RegistrationWatcher:
    """Subscribe to ``pending_registrations`` UPDATE events for a single Discord user.

    One watcher per ``/register`` invocation: it keeps a private channel open
    until the matching row's ``completed`` column flips to ``true`` (success
    path) or the caller cancels it (timeout / cleanup path).
    """

    def __init__(
        self,
        supabase: AsyncClient,
        discord_id: int,
        on_complete: RegistrationCallback,
    ) -> None:
        """Initialise a watcher for one Discord user's pending registration.

        :param supabase: shared async Supabase client used for the realtime channel
        :type supabase: AsyncClient
        :param discord_id: Discord snowflake of the user being watched
        :type discord_id: int
        :param on_complete: coroutine called once with ``discord_id`` on completion
        :type on_complete: RegistrationCallback
        """
        self.supabase = supabase
        self.discord_id = discord_id
        self.on_complete = on_complete
        self._channel: Any | None = None
        self._fired = asyncio.Event()

    async def start(self) -> None:
        """Open the realtime channel and register the postgres-changes callback."""
        channel = self.supabase.channel(f"reg_{self.discord_id}")
        channel.on_postgres_changes(
            event="UPDATE",
            schema="public",
            table="pending_registrations",
            filter=f"discord_id=eq.{self.discord_id}",
            callback=self._on_change,
        )
        await channel.subscribe()
        self._channel = channel
        log.debug(f"realtime: subscribed reg_{self.discord_id}")

    async def stop(self) -> None:
        """Tear down the realtime channel; safe to call multiple times."""
        if self._channel is None:
            return
        try:
            await self.supabase.remove_channel(self._channel)
        except Exception as e:
            # Cleanup failures should never break the bot; log and move on
            log.warning(f"realtime: failed to remove channel reg_{self.discord_id}: {e}")
        finally:
            self._channel = None

    def _on_change(self, payload: dict) -> None:
        """Realtime callback; schedules ``on_complete`` when the row is marked complete.

        :param payload: postgres-changes event payload from supabase realtime
        :type payload: dict
        """
        log.debug(f"realtime: _on_change fired for discord_id={self.discord_id}, payload={payload!r}")

        # Discard duplicates — supabase fires once per UPDATE but be defensive
        if self._fired.is_set():
            return

        # Extract the row payload (shape varies slightly across realtime versions)
        new_row = (
            payload.get("data", {}).get("record")
            or payload.get("record")
            or payload.get("new")
            or {}
        )
        log.debug(f"realtime: new_row={new_row!r}")

        # Confirm completion + identity match before firing
        if not new_row.get("completed"):
            log.debug(f"realtime: completed not set, ignoring")
            return
        if int(new_row.get("discord_id", 0)) != self.discord_id:
            log.debug(f"realtime: discord_id mismatch, ignoring")
            return

        self._fired.set()
        asyncio.create_task(self._fire())

    async def _fire(self) -> None:
        """Invoke the user-supplied callback then tear down the channel."""
        try:
            await self.on_complete(self.discord_id)
        except Exception as e:
            log.exception(e)
        finally:
            await self.stop()


class RealtimeManager:
    """Owns the shared Supabase realtime client and tracks active watchers.

    Acts as a registry so the same Discord user re-running ``/register`` doesn't
    leak overlapping channels: a new watcher cancels the previous one.
    """

    def __init__(self, supabase: AsyncClient) -> None:
        """Initialise with an already-connected async Supabase client.

        :param supabase: shared async Supabase client
        :type supabase: AsyncClient
        """
        self.supabase = supabase
        self._watchers: dict[int, RegistrationWatcher] = {}

    async def watch(self, discord_id: int, on_complete: RegistrationCallback) -> None:
        """Begin watching ``pending_registrations`` for the given Discord user.

        Replaces any existing watcher for the same user.

        :param discord_id: Discord snowflake of the user being watched
        :type discord_id: int
        :param on_complete: coroutine called once with ``discord_id`` on completion
        :type on_complete: RegistrationCallback
        """
        # Drop any prior watcher for this user before opening a fresh channel
        existing = self._watchers.pop(discord_id, None)
        if existing is not None:
            await existing.stop()

        watcher = RegistrationWatcher(self.supabase, discord_id, on_complete)
        await watcher.start()
        self._watchers[discord_id] = watcher

    async def cancel(self, discord_id: int) -> None:
        """Stop watching the given user's pending registration, if any.

        :param discord_id: Discord snowflake of the user being watched
        :type discord_id: int
        """
        watcher = self._watchers.pop(discord_id, None)
        if watcher is not None:
            await watcher.stop()

    async def close(self) -> None:
        """Tear down every active watcher; call during bot shutdown."""
        for watcher in list(self._watchers.values()):
            await watcher.stop()
        self._watchers.clear()
