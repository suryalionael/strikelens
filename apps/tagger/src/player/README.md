# player/

Video player for a local fight file. The file is opened with an object URL and
never leaves the browser.

- `time.ts`: pure helpers. Time formatting (`mm:ss.mmm`, and `m:ss` or `h:mm:ss` for
  the seek bar), parsing a go-to time, frame index, frame step, jumps.
- `keys.ts`: maps `Space`, `←`, `→` to player actions, and `Shift`/`Alt` with the
  arrows to 5 s and 30 s jumps. Ignores keys typed into form controls and keys
  with `Ctrl` or `Cmd`.
- `SeekBar.tsx`: a seek bar over the whole video with the time under the pointer,
  and a Go to field. After a click or drag the bar gives the keyboard back, so
  `Space` and the arrows keep working.
- `usePlayerState.ts`: owns the `<video>` element and mirrors its state into React.
- `PlayerProvider.tsx` and `PlayerContext.ts`: share the player. Any component
  inside `PlayerProvider` calls `usePlayer()` to read `currentTime`, `playing`,
  `rate`, `fps`, and the controls (`seek`, `pause`, `stepFrame`, ...).
- `VideoPlayer.tsx`: the UI.

## Frame rate

Browsers do not expose a video's frame rate, so the analyst picks it (default
30 fps). Frame steps seek to the middle of the target frame, so the browser shows
that frame and not its neighbour. Stepping pauses playback first.
