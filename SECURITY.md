# Security policy

## Supported versions

StrikeLens is pre-1.0. Only the latest commit on `main` gets fixes.

## Reporting a vulnerability

Do not open a public issue for security problems.

Use GitHub's private reporting instead: go to the repo's **Security** tab and click
**Report a vulnerability**. If that is not available, email suryalionael@gmail.com
with "StrikeLens security" in the subject.

Include what you found, how to reproduce it, and what an attacker could do with it.
You should get a reply within 7 days.

## Data exposure

If you find footage, frames, keypoints, labels, or model weights committed to this
repo, report it the same way. Those files must never be in git (see
[docs/data-policy.md](docs/data-policy.md)), and we will remove them from history.
