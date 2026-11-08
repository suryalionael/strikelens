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
and elbow.

Byon fights under the UCC Kickstriking rules (see [rules.md](rules.md)). They
allow slicing elbows, so `elbow` stays. They also allow the backfist, the
spinning backfist, and other spinning and flying strikes, which this list cannot
describe yet. Whether Freefly counts them as their own categories is open
question 9 (see
[stat-definitions.md](stat-definitions.md#open-questions-for-freefly)).
Provisional: until Freefly answers, tag them with the closest weapon (a backfist
as `hook`, a spinning kick as `kick`). This choice changes the weapon mix, so it
is revisited with the answer.

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
| Red | `Q` |
| Blue | `W` |
| **Suggestions** (with Review suggestions on) | |
| Confirm suggestion | `Enter` |
| Reject suggestion | `X` |
| Next suggestion | `Tab` |
| Previous suggestion | `Shift+Tab` |
| **Playback** | |
| Play / pause | `Space` |
| Frame step back / forward | `←` / `→` |
| Jump 5 s back / forward | `Shift+←` / `Shift+→` |
| Jump 30 s back / forward | `Alt+←` / `Alt+→` (`Option` on macOS) |
| **Editing** | |
| Undo last change (new tag, edit, or delete) | `Ctrl+Z` (`Cmd+Z` on macOS) |

The player also has a seek bar over the whole video and a **Go to** field that
takes `m:ss` or `h:mm:ss`. The usual video-site keys (`J`, `L`, `0`-`9`) are
tagging keys here, so jumps use `Shift` and `Alt` with the arrows.

The suggestion keys work while **Review suggestions** is on. Then the weapon,
outcome, target, and fighter keys change the current suggestion instead of
starting a new tag. A suggestion is confirmed only with a weapon, an outcome, and
a target, and keeps `source: cv` and its `confidence`.

### How a tag is entered

The tagger keeps a draft tag. Each key fills one field. When the draft has a
fighter, weapon, outcome, and target, it saves at the video time when the first
key of the draft was pressed. The fighter stays selected between tags, so most
tags need only three keys: weapon, outcome, target.

Example: `Q` `K` `L` `2` = red, kick, landed, body.

Rules (issue #8):

- Keys can come in any order. Pressing a key for a field that is already set
  replaces it, so a wrong weapon is fixed by pressing the right one.
- The draft's time is the video time at its first key. That includes the fighter
  key when it starts a draft.
- `Esc` clears the draft. The fighter stays selected.
- There is no timeout. A draft waits until it is complete or cleared.
- The round comes from the round marks. A tag outside every marked round is not
  saved, and the tagger says why.
- Keys typed into a text field or a select are ignored, and so are keys with
  `Ctrl`, `Cmd`, or `Alt`.

### Fighter keys

`Q` = red, `W` = blue. See [ADR 0005](decisions/0005-fighter-hotkeys.md) for the
options considered.
