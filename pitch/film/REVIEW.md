# Review

## Creative calls
- Built storyline A, "One night, one ID" (STORYLINES.md): one pregnant woman at 2:07 AM, carried from "which hospital
  can actually help?" to "a hospital is ready for you". B (the ID as the camera's subject) and C (three phones in split
  screen) are written but not built.
- Every app screen is a real capture of the running app at 2x (tools: Puppeteer against the local dev app, synthetic
  demo data). Only the browser's permission sheets and the lock-screen notification are drawn, with the app's real
  wording ("Hospital is ready", "Abeokuta Central Hospital is ready for you.").
- Permissions shown: location (browser), notifications (browser), and the patient's own consent (Allow / Don't allow,
  Who looked, Stop, one-time QR).
- NHIA (formerly NHIS) appears as a feature, not a criticism: the patient's NHIA number travels with her VITALIS ID
  and reception can see and correct it.
- Length 62 s (a minute, plus a held end card). Colours, type and icon are the app's own.

## Measured
- `hyperframes check`: ok. Kept on purpose:
  - `text_below_floor` x3: the browser's permission sheet inside the phone is phone-sized (22-28 px), like the real one.
  - `line_unread` x3 on the end card: snapshots at 59.4 s, 60.4 s and 61.6 s show the mark, URL and footnote on screen
    for about 2.6 s; the checker's 0.37 s is a sampling artefact.
- Snapshots of every beat, every seam and the phone sheet were looked at.

## Not checked
- The sound was placed by time, not heard. There is no music bed yet: add one (HeyGen music catalog after
  `heygen auth login --oauth`, or a local MusicGen track) and duck the effects 3-6 dB under it.

## Weakest shot and next steps
- The hospital Incoming card (22-24 s) sits in the left half of the frame; a slow push toward Accept would give it more
  weight.
- With more time: a music bed with the payoff (the notification at ~26 s) and the mark (~58.5 s) on strong beats.
