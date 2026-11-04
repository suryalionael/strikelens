# Tag schema and hotkeys

A **tag** is one strike attempt. The machine-readable definition is
[`shared/schema/tag.schema.json`](../shared/schema/tag.schema.json). This page
explains it for people.

Human tags and CV suggestions use the same schema. A suggestion is a tag with
`source: "cv"`, a `confidence`, and a `status` that starts at `pending`.

## Fields

| Field | Type | Values | Notes |
|---|---|---|---|
| `id` | UUID | | Unique per tag |
| `fight_id` | UUID | | Fight the tag belongs to |
| `round` | integer | 1, 2, 3... | Set from the round the timestamp falls in |
| `timestamp_ms` | integer | >= 0 | Video time of the strike, ms from file start |
| `fighter` | enum | `red`, `blue` | Who threw the strike |
| `weapon` | enum or null | see below | Null only on a CV suggestion with no weapon guess |
| `outcome` | enum or null | `landed`, `missed`, `blocked` | Null until an analyst sets it |
| `target` | enum or null | `head`, `body`, `legs` | Null until an analyst sets it |
| `source` | enum | `human`, `cv` | Who created it |
| `confidence` | number or null | 0.0-1.0 | Required for `cv`, must be null for `human` |
| `status` | enum | `pending`, `confirmed`, `rejected` | Only `confirmed` counts in stats |
| `created_by` | string | | Analyst username, or model name and version |
| `created_at` | datetime | ISO 8601 UTC | |

A `confirmed` tag must have a weapon, outcome, and target.

## Strike taxonomy

### Weapons

| Weapon | Group | Description |
|---|---|---|
| `jab` | Punch | Lead-hand straight punch |
| `cross` | Punch | Rear-hand straight punch |
| `hook` | Punch | Curved punch from either hand |
| `uppercut` | Punch | Rising punch from either hand |
| `kick` | Kick | Any round kick: head, body, or leg |
| `teep` | Kick | Push kick with the ball of the foot or heel |
| `knee` | Knee | Any knee strike |
| `elbow` | Elbow | Any elbow strike |

The "Group" column is how the stats page rolls weapons up into punch, kick, knee,
and elbow. Whether Byon's rules allow elbows, and whether Freefly counts spinning
or backfist strikes as their own category, are open questions (see
[stat-definitions.md](stat-definitions.md#open-questions-for-freefly)).

### Outcomes

| Outcome | Meaning in v1 |
|---|---|
| `landed` | The strike connected with the target |
| `missed` | The strike did not connect |
| `blocked` | The strike was stopped by a guard, check, or parry |

The exact line between these, especially landed vs blocked, is not settled. It
is the first open question for Freefly.

### Targets

| Target | Meaning |
|---|---|
| `head` | Head and neck |
| `body` | Torso, including arms when they cover the torso (to confirm) |
| `legs` | Hips down |

For a missed strike, the target is where it was aimed.

## Default hotkeys

One key per choice, no modifiers, so the analyst can keep one hand on the keyboard.

| Action | Key |
|---|---|
| **Weapon** | |
| Jab | `J` |
| Cross | `C` |
| Hook | `H` |
| Uppercut | `U` |
| Kick | `K` |
| Knee | `N` |
| Elbow | `E` |
| Teep | `T` |
| **Outcome** | |
| Landed | `L` |
| Missed | `M` |
| Blocked | `B` |
| **Target** | |
| Head | `1` |
| Body | `2` |
| Legs | `3` |
| **Fighter** | |
| Red | `Q` (proposed, see below) |
| Blue | `W` (proposed, see below) |
| **Suggestions** | |
| Confirm suggestion | `Enter` |
| Reject suggestion | `X` |
| Next suggestion | `Tab` |
| Previous suggestion | `Shift+Tab` |
| **Playback** | |
| Play / pause | `Space` |
| Frame step back / forward | `←` / `→` |
| **Editing** | |
| Undo last tag | `Ctrl+Z` (`Cmd+Z` on macOS) |

### How a tag is entered

The tagger keeps a draft tag. Each key fills one field. When the draft has a
fighter, weapon, outcome, and target, it saves at the video time when the first
key of the draft was pressed. The fighter stays selected between tags, so most
tags need only three keys: weapon, outcome, target.

Example: `Q` `K` `L` `2` = red, kick, landed, body.

The exact draft behaviour (timeouts, what `Esc` does, whether the order of keys
is free) is part of issue #8.

### Decision to confirm: fighter keys

The brief suggested `R` for red and `B` for blue. `B` is already Blocked, so that
does not work.

**Proposal:** `Q` = red, `W` = blue.

- Both sit under the left hand, next to each other, and are not used for anything else.
- Left hand picks the fighter, right hand picks the weapon and outcome. Number keys
  sit in between for targets.
- `R` and `B` stay free, so `B` = Blocked is unambiguous.

Alternatives considered:

- `R` = red, `Shift+B` = blue: inconsistent, and `Shift+B` is easy to mistype as `B`.
- One toggle key (for example `` ` ``): fewer keys, but the analyst has to look at
  the screen to know which fighter is active.
- `Blocked` moved to another key, keep `R`/`B` for fighters: `B` for blue is the most
  natural, but then Blocked needs a non-obvious key like `O`.

Status: **proposed, not confirmed.** The owner decides before building issue #8.
Freefly is not contacted until Phase 4, so this does not wait for them. Record the
final choice as an ADR. Hotkeys should be configurable later, so this is a default, not
a lock-in.
