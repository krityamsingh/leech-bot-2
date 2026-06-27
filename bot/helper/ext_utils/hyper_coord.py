"""Global fair-share coordinator for HyperDL/HyperUL transfers.

Problem it solves
-----------------
Telegram rate-limits **per account**, not per file. Each HyperDL/HyperUL
instance is greedy: by default it tries to open HYPER_PIPELINE in-flight
requests and HYPER_THREADS workers *per file*. When N files run at once on
the **same single account**, all N pile ~N * pipeline requests onto that one
account → instant self-induced FloodWait → every file slows every other file
down and the aggregate throughput collapses.

How it works
------------
A per-account in-flight budget is divided **fairly** across the transfers
currently using that account:

  share = budget / active_transfers_on_account

- 1 file  → full budget (full speed)
- 10 files → ~1/10 of the budget each (stable, no self-flood)
- 4 accounts, 10 files → accounts get load-balanced so each file lands on
  its own account wherever possible and hits full speed again.

Callers obtain a ``CoordHandle`` via ``register(...)`` and call ``release()``
in a ``finally``. The handle's ``share_factor`` (0..1, of the per-account
budget) and the absolute ``pipeline_depth`` are read live so a transfer's
window automatically relaxes as siblings start/finish.

This is process-global and lock-free for the hot read path: budgets are
updated under a single lock only on register/release, and the live counters
are plain ints (GIL-protected reads) that every in-flight part re-reads.
"""

from __future__ import annotations

from asyncio import Lock
from typing import Dict, List, Tuple

from ... import LOGGER
from ...core.config_manager import Config

# Per-account ceiling on concurrent in-flight MTProto requests.
# Telegram tolerates roughly this many simultaneous GetFile/SaveFilePart
# requests per session before FloodWait kicks in. It is shared across every
# file using that account and divided evenly (fair share). 128 is an
# aggressive ceiling for fast single-file throughput; the additive-increase
# in _pipeline_fetch self-corrects down on any FloodWait.
DEFAULT_PER_ACCOUNT_BUDGET = 128

# Absolute floor so a single transfer never collapses to a useless window.
_MIN_PIPELINE = 8

# Total in-flight requests the bot as a whole should try to sustain. Used as
# the global pool when more than one account is available, so aggregate
# throughput scales with account count instead of being pinned to one.
DEFAULT_GLOBAL_BUDGET = 512


class _AccountState:
    __slots__ = ("active", "budget")

    def __init__(self, budget: int):
        self.active = 0          # number of transfers currently using this account
        self.budget = budget     # in-flight request slots reserved for this account


class HyperCoordinator:
    """Process-wide registry of active transfers keyed by account id.

    Keyed by ``id(client)`` so that the same underlying Pyrogram Client object
    used by several helper structures is counted once.
    """

    def __init__(self):
        self._lock = Lock()
        self._accounts: Dict[int, _AccountState] = {}
        # total budget across all accounts, grows as accounts register
        self._total_budget = DEFAULT_GLOBAL_BUDGET

    # -- accounting ------------------------------------------------------
    async def register(
        self, clients: List, *, is_upload: bool = False
    ) -> "CoordHandle":
        """Claim a fair slice for a transfer across the given ``clients``.

        All listed clients are marked active so their budget is shared with
        this transfer. Returns a handle whose ``share_factor`` and
        ``pipeline_depth`` reflect the current fair split.
        """
        async with self._lock:
            for client in clients:
                st = self._accounts.get(id(client))
                if st is None:
                    st = _AccountState(self._per_account_budget())
                    self._accounts[id(client)] = st
                st.active += 1
            # total budget = sum of per-account budgets actually in use
            self._total_budget = sum(
                a.budget for a in self._accounts.values() if a.active
            ) or DEFAULT_GLOBAL_BUDGET
        return CoordHandle(self, clients, is_upload=is_upload)

    async def release(self, clients: List) -> None:
        async with self._lock:
            for client in clients:
                st = self._accounts.get(id(client))
                if st is None:
                    continue
                st.active = max(0, st.active - 1)
                if st.active == 0:
                    # keep the slot so re-registration is cheap, but stop
                    # counting it toward the global budget
                    pass
            self._total_budget = sum(
                a.budget for a in self._accounts.values() if a.active
            ) or DEFAULT_GLOBAL_BUDGET

    # -- live read path (no lock; int reads are atomic under the GIL) ----
    def _per_account_budget(self) -> int:
        cfg = Config.HYPER_PIPELINE or DEFAULT_PER_ACCOUNT_BUDGET
        return max(_MIN_PIPELINE, cfg)

    def _active_on(self, client) -> int:
        st = self._accounts.get(id(client))
        return st.active if st else 1

    def share_factor(self, client) -> float:
        """Fraction (0..1] of ``client``'s budget this one transfer gets.

        With ``k`` transfers sharing an account, each gets ``1/k``.
        """
        n = self._active_on(client)
        return 1.0 / n if n > 0 else 1.0

    def pipeline_depth(self, client, configured: int) -> int:
        """Fair in-flight window for one part on ``client``.

        ``configured`` is the per-file value (HYPER_PIPELINE) the caller would
        have used alone. The coordinator never lets it exceed the fair share
        of the account's budget, so concurrent files can't self-flood.
        """
        budget = self._per_account_budget()
        n = self._active_on(client)
        fair = budget // n if n > 0 else budget
        depth = min(configured or budget, fair)
        return max(_MIN_PIPELINE, depth)


class CoordHandle:
    """Released via ``await handle.release()`` in a ``finally`` block."""

    __slots__ = ("_coord", "_clients", "is_upload", "_released")

    def __init__(self, coord: HyperCoordinator, clients: List, is_upload: bool):
        self._coord = coord
        # dedupe by id() — a client may appear via several helper structures
        seen = set()
        self._clients = [c for c in clients if not (id(c) in seen or seen.add(id(c)))]
        self.is_upload = is_upload
        self._released = False

    @property
    def share_factor(self) -> float:
        # use the first client as the representative; for downloads all
        # picked clients share the same budget pool, uploads use a single one
        c = self._clients[0] if self._clients else None
        return self._coord.share_factor(c) if c is not None else 1.0

    def pipeline_depth(self, configured: int) -> int:
        c = self._clients[0] if self._clients else None
        if c is None:
            return max(_MIN_PIPELINE, configured or DEFAULT_PER_ACCOUNT_BUDGET)
        return self._coord.pipeline_depth(c, configured)

    async def release(self) -> None:
        if self._released:
            return
        self._released = True
        await self._coord.release(self._clients)


# Singleton. Importers use this directly.
coordinator = HyperCoordinator()


def _log_state(tag: str) -> None:
    """Debug helper — uncomment calls if diagnosing share fairness."""
    active = [(k, s.active) for k, s in coordinator._accounts.items() if s.active]
    LOGGER.debug(
        f"HyperCoord {tag}: active_accounts={active} total_budget={coordinator._total_budget}"
    )
