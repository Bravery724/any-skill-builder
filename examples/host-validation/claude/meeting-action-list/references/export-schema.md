# Export schema (CSV / JSON)

Use this schema only when the user asks for an export. Values must match the action table exactly.

## Fields

| Field | Type | Meaning |
|---|---|---|
| `id` | integer | Row number from the table |
| `action` | string | The verb-first action text |
| `owner` | string | Owner exactly as written. Use `"missing"` if none. Inferred owners keep the ` (inferred)` suffix. Conflicts use `"conflicting: A (line n) vs B (line m)"`. |
| `due_text` | string | Original due-date wording, or `"missing"` |
| `due_date` | string or null | Resolved ISO date (`YYYY-MM-DD`) only when an explicit date or an anchored relative date allows it; otherwise `null` |
| `flags` | array of strings | Any of `missing_owner`, `missing_date`, `conflict`, `shared_owner`, `vague_date`, `ambiguous_relative_date`, `vague_action`, `possible_duplicate`, `date_check` |
| `source` | string | Short quote or line reference from the notes |

Possible action items and decisions are **not** exported unless the user asks. If they ask, add them as separate arrays, `possible_items` and `decisions`, containing plain strings.

## JSON shape

```json
{
  "meeting_date": "2026-03-10",
  "items": [
    {"id": 1, "action": "Send revised pricing deck to Acme", "owner": "PK", "due_text": "Fri", "due_date": "2026-03-13", "flags": [], "source": "PK send rev. deck to Acme Fri"}
  ]
}
```

Use `"meeting_date": null` when it is unknown.

## CSV

Use the header `id,action,owner,due_text,due_date,flags,source`. Join flags with `;`. Quote any field that contains commas or quotes, following RFC 4180, and leave `due_date` empty when it is null.
