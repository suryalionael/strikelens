# export/

Export stat cards to PNG (Instagram 4:5) and tag data to CSV. See issue #15.

- `csv.ts`: pure. The tags CSV has every confirmed tag, one column per field of
  `tag.schema.json`, in schema order. The stats CSV is long format
  (`group,item,fighter,metric,value`) so it pivots cleanly; null values are empty
  cells. Text that a spreadsheet would run as a formula gets a leading apostrophe.
- `cards.ts`: pure. Builds the carousel: headline, attempts per round, weapon mix,
  and target distribution. Every number comes from the stats endpoint.
- `draw.ts`: draws one 1080x1350 card on a canvas. Same header and footer on every
  card: event, date, fighters, credit line, a provisional-definitions note, and
  the card number.
- `download.ts`: browser I/O. Renders, makes the PNG, and starts the download.
  Nothing is uploaded.
- `ExportPanel.tsx`: the buttons and card previews, at the bottom of the stats panel.

Cards contain no fight footage or frames, so they are safe to share under
[docs/data-policy.md](../../../../docs/data-policy.md). The credit line wording
is provisional until agreed with Freefly; the analyst can edit it before export.
