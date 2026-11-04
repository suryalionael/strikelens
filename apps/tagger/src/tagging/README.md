# tagging/

Hotkey tagging. See issue #8 and the rules in
[docs/tag-schema.md](../../../../docs/tag-schema.md#how-a-tag-is-entered).

- `hotkeys.ts`: every key binding in one config object (`DEFAULT_HOTKEYS`). Fighter
  keys follow [ADR 0005](../../../../docs/decisions/0005-fighter-hotkeys.md).
- `engine.ts`: pure reducer. Keys fill a draft; a complete draft comes back as
  `complete`, timed at its first key.
- `tags.ts`: pure. Finds the round for a time and builds the API tag.
- `TagPanel.tsx`: listens for keys, saves tags through the API, shows the draft
  and the latest tags. No tagging logic lives here.
