# 0007. Round suggestions from scoreboard presence, not clock OCR

- **Status:** accepted
- **Date:** 2026-11-07
- **Issue:** #35

## Context

The analyst marks where each round starts and ends before tagging. In a 20 to 60
minute broadcast that means scrubbing for every round. Byon broadcasts show a
scoreboard during each round (event logo, "N OF M", a countdown clock from 3:00,
and both names), and hide it between rounds.

## Options

- **Read the clock with OCR** (Tesseract or EasyOCR). Exact times, but a new
  dependency (a system binary, or PyTorch for EasyOCR), and digit reading tuned
  per graphic style.
- **Templates of each event's scoreboard.** Simple matching, but the templates
  are crops of Byon's broadcast, which may not be committed (data-policy.md).
- **Scoreboard presence, template-free.** In the bottom left of the frame, the
  patch that looks the same in the most frames is the scoreboard's logo: live
  video behind it keeps changing. Round times then follow from when it shows.

## Decision

Scoreboard presence, template-free. A round starts when the scoreboard appears
and runs 3 minutes of clock time. Gaps under 15 s are bridged. A stretch that
ends early, followed by one that makes up the rest of the 3 minutes, is one
round with a pause (a doctor's check). A round whose scoreboard goes away more
than 20 s early is suggested as ending there and marked for the analyst to check.

Measured on five practice fights (two at 10 fps, three whole broadcasts at 1 fps):

| Fight | Rounds | Result |
|---|---|---|
| Tryout 2, Aditya vs Franky | 2 (stoppage in round 2) | Both found. Starts within 1 s of the scoreboard clock. Round 2 marked to check: right, it was a knockdown. |
| Madness 4, Waruwu vs Londo | 3 | 3 full rounds |
| Madness 2, Londo vs Rifandi | 3 | 3 full rounds |
| Showbiz 6, Siahaan vs Abdullah | 5 | 5 found. Round 5 kept whole across a 64 s medical pause (end about 8 s late). Round 2 marked to check: the broadcast hid the scoreboard for its last minute. |
| Madness 4, round 1 excerpt | 1 (cut mid-round) | Found, marked to check |

## Consequences

- No new dependency and nothing of Byon's in the repo.
- Starts are as exact as the sampling (1 s). Ends are estimated from the round
  length, so a hidden scoreboard, a stopped clock, or a stoppage needs a look;
  those rounds are marked "check the end".
- A scoreboard outside the bottom left needs `scoreboard_region` changed.
- Revisit with clock OCR if the analyst spends real time fixing round ends.
