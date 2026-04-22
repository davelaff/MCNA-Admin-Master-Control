"""
Registry CRUD tools for Secure SketCH.

Manages versioned key→entry mappings used as registry-backed evidence
(approved software lists, allowed ports, approved vendors, etc.).
"""

import json
import uuid

from db import get_connection
from tools.ssk_common import (
    RegistryConflictError,
    append_activity,
    json_error,
    json_ok,
    utc_now,
)


def registry_add(
    registry_name: str,
    entry_key: str,
    entry_data: dict,
    control_ids: list[str],
    pointer: str | None = None,
    effective_from: str | None = None,
) -> str:
    """Add a new active entry to a named registry.

    Raises RegistryConflictError (returned as JSON error) when an active entry
    for ``(registry_name, entry_key)`` already exists.
    """
    entry_id = str(uuid.uuid4())
    now = utc_now()
    eff_from = effective_from or now

    try:
        with get_connection() as conn:
            existing = conn.execute(
                "SELECT registry_entry_id FROM ssk_registries "
                "WHERE registry_name=? AND entry_key=? AND status='active'",
                (registry_name, entry_key),
            ).fetchone()
            if existing:
                raise RegistryConflictError(
                    f"active registry entry already exists for {registry_name}:{entry_key}"
                )

            conn.execute(
                """
                INSERT INTO ssk_registries
                    (registry_entry_id, registry_name, control_ids, entry_key,
                     entry_data, entry_pointer, status, effective_from,
                     effective_to, recorded_at)
                VALUES (?,?,?,?,?,?,'active',?,NULL,?)
                """,
                (
                    entry_id,
                    registry_name,
                    json.dumps(control_ids, sort_keys=True),
                    entry_key,
                    json.dumps(entry_data, sort_keys=True),
                    pointer,
                    eff_from,
                    now,
                ),
            )

            row = conn.execute(
                "SELECT * FROM ssk_registries WHERE registry_entry_id=?",
                (entry_id,),
            ).fetchone()
            result = dict(row)

        append_activity(
            "registry_add",
            "success",
            {"registry_name": registry_name, "entry_key": entry_key},
            entity_id=entry_id,
        )
        return json_ok(result)

    except RegistryConflictError as exc:
        append_activity(
            "registry_add",
            "error",
            {"registry_name": registry_name, "entry_key": entry_key, "conflict": True},
        )
        return json_error(str(exc), "RegistryConflictError")


def registry_list(
    registry_name: str | None = None,
    status: str = "active",
) -> str:
    """Return registry entries, optionally filtered by registry name and status."""
    with get_connection() as conn:
        if registry_name is not None:
            rows = conn.execute(
                "SELECT * FROM ssk_registries WHERE registry_name=? AND status=? "
                "ORDER BY registry_name, entry_key",
                (registry_name, status),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM ssk_registries WHERE status=? "
                "ORDER BY registry_name, entry_key",
                (status,),
            ).fetchall()

    return json_ok([dict(r) for r in rows])


def registry_get(
    registry_name: str,
    entry_key: str,
    include_retired: bool = False,
) -> str:
    """Return a single registry entry by name + key.

    By default returns only the active entry.  Pass ``include_retired=True``
    to also match retired entries (most-recently-recorded first).
    """
    with get_connection() as conn:
        if include_retired:
            row = conn.execute(
                "SELECT * FROM ssk_registries WHERE registry_name=? AND entry_key=? "
                "ORDER BY recorded_at DESC LIMIT 1",
                (registry_name, entry_key),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM ssk_registries WHERE registry_name=? AND entry_key=? "
                "AND status='active'",
                (registry_name, entry_key),
            ).fetchone()

    if row is None:
        return json_error(
            f"no {'entry' if not include_retired else 'entry (active or retired)'} "
            f"found for {registry_name}:{entry_key}",
            "NotFound",
        )

    return json_ok(dict(row))


def registry_retire(
    registry_name: str,
    entry_key: str,
    reason: str,
) -> str:
    """Mark the active entry for ``(registry_name, entry_key)`` as retired.

    Embeds ``retire_reason`` in ``entry_data`` and sets ``effective_to``.
    """
    now = utc_now()

    with get_connection() as conn:
        current = conn.execute(
            "SELECT * FROM ssk_registries WHERE registry_name=? AND entry_key=? AND status='active'",
            (registry_name, entry_key),
        ).fetchone()

        if current is None:
            return json_error(
                f"no active entry found for {registry_name}:{entry_key}",
                "NotFound",
            )

        entry_id = current["registry_entry_id"]
        raw_data = current["entry_data"]
        try:
            payload = json.loads(raw_data) if raw_data else {}
        except (json.JSONDecodeError, TypeError):
            payload = {}

        payload["retire_reason"] = reason

        conn.execute(
            "UPDATE ssk_registries SET status='retired', effective_to=?, entry_data=? "
            "WHERE registry_entry_id=?",
            (now, json.dumps(payload, sort_keys=True), entry_id),
        )

        row = conn.execute(
            "SELECT * FROM ssk_registries WHERE registry_entry_id=?",
            (entry_id,),
        ).fetchone()
        result = dict(row)

    append_activity(
        "registry_retire",
        "success",
        {"registry_name": registry_name, "entry_key": entry_key, "reason": reason},
        entity_id=entry_id,
    )
    return json_ok(result)
