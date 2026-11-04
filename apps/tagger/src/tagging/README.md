# tagging/

Hotkey tagging. See issue #8 and the rules in
[docs/tag-schema.md](../../../../docs/tag-schema.md#how-a-tag-is-entered).

- `hotkeys.ts`: every key binding in one config object (`DEFAULT_HOTKEYS`). Fighter
  keys follow [ADR 0005](../../../../docs/decisions/0005-fighter-hotkeys.md).
- `engine.ts`: pure reducer. Keys fill a draft; a complete draft comes back as
  `complete`, timed at its first key.
- `tags.ts`: pure. Finds the round for a time and builds the API tag.
- `TagPanel.tsx`: listens for keys, saves tags through the API, shows the draft
  and the latest tags. Every option is also a button that sends the same action
  as its key (`actionFor`), so clicking and typing behave the same. No tagging
  logic lives here.
- `timelineLayout.ts`: pure. The visible time range (the marked rounds, or the
  whole video before any are marked), positions, round bands, and markers. Outcome
  is shown by shape: filled = landed, ring = missed, square = blocked.
- `Timeline.tsx`: red and blue lanes with round bands and a playhead. Click a
  marker or the track to seek. Markers are memoised so the playhead can move every
  frame without redrawing them.
- `edits.ts`: pure. Turns an edit into a PATCH; a new time also moves the tag to
  its round, and a time outside every round is refused.
- `history.ts`: pure undo history (50 steps). Undo deletes a new tag, restores a
  deleted tag with the same id and creation time, or reverts an edit.
- `TagEditor.tsx`: change or delete the selected tag. Delete asks first.
