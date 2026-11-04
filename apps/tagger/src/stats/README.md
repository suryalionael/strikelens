# stats/

Stat cards and charts. Components here only display numbers from
`GET /fights/{id}/stats`; every stat is calculated in `apps/api/app/stats/core.py`.
See `docs/stat-definitions.md` and issues #13-#14.

- `format.ts`: pure. Formats values (a dash for null, never 0) and reshapes the
  response into red/blue rows for charts. It never derives a new stat.
- `HeadlineCard.tsx`: attempts, landed, accuracy, strikes per minute per fighter.
- `CornerBarChart.tsx`: grouped red/blue bars with a table view underneath.
- `StatsPanel.tsx`: fetches stats, refreshes after each saved tag or round change,
  and lists the provisional rules the numbers follow.
- `colors.ts`: corner colours, validated with the dataviz palette checks.
