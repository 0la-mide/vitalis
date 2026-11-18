# Brief: the silent VITALIS film (v2)

You are making a finished video file, not a plan. Work until `VITALIS-film-silent.mp4` exists, has been checked
frame by frame, and matches this brief.

## 1. Tools

- **Use the `/hyperframes` skill.** Read it first, before you write anything. It holds the render contract and the
  work loop. Use `/hyperframes-cli` for scaffold, check, snapshot and render, and look in `/hyperframes-registry`
  before you hand-build a transition or a title.
- Do **not** use `/media-use` for sound. This film has no sound at all (see section 5).
- If HyperFrames is not available, use any HTML-to-video tool that renders deterministically, and keep every rule
  below.

## 2. Where everything is

All files are in **`~/Downloads/vitalis/v2/`**:

| File | What it is |
|---|---|
| `VITALIS-video-assets.zip` | everything the film uses. Unzip it in place to `~/Downloads/vitalis/v2/VITALIS-video-assets/` |
| `VIDEO-PROMPT-SILENT.md` | this brief (a copy is also inside the zip) |
| `VITALIS-teleprompter.pdf` | what the presenter says over the film. The scene start times below must not move, because the script is timed to them |
| `VITALIS-presentation.pptx` | the deck, for reference only (look and tone) |

Inside `VITALIS-video-assets/`:

- `brand/icon.png`: the real VITALIS icon. Never redraw it.
- `fonts/ibm-plex-sans-latin-{400,500,600,700}-normal.woff2`: the only font. Load these with `@font-face`.
- `screens/`: real screenshots of the app, taken at 2x. **P_** = patient phone (780×1688, put inside a thin dark
  phone bezel), **D_** = desktop or hospital screen (on a white card with a soft shadow), **U_** = a basic phone on
  USSD. U_ images already include the phone body: no bezel, and show them on their own.

### Screens (the ones this film uses)

| File | Shows |
|---|---|
| P_home | home: "What is happening?" with 8 emergency buttons |
| P_body | body map, pregnant woman |
| P_symptoms | "What do you see?" with Heavy bleeding |
| P_emergency | emergency plan: Call 112, first hospital card "Ready" |
| P_waiting | request sent, waiting for the hospital |
| P_accepted | "Go now. They are ready for you." with a map |
| P_emergency_amb | emergency plan with **Call 112** and **Call ambulance: Ogun State Ambulance · 0811 200 0033** |
| P_home_amb | bottom of home: Call 112, Call ambulance, "No smartphone or no data? Dial *384*8482#" |
| P_offline | emergency plan with no signal: grey "No signal" panel, badges Accepts NHIA and Free maternal care |
| P_saved, P_sent | request saved with no signal, then sent when the signal returns |
| P_worker, P_month | chemist walk-in triage, then the chemist's month |
| P_addrecord, P_record2 | she adds an allergy, then her record with "Reported by you" |
| P_request, P_wholooked, P_share | Allow or Don't allow, Who looked, QR code |
| D_incoming | hospital Incoming card with Accept / Decline |
| D_outbox | hospital screen with no signal: "1 saved on this phone…" |
| D_safety, D_prescribe | AI safety alert, prescription blocked |
| D_coverage | Cost and coverage: Accepts NHIA, Free maternal care |
| D_reception, D_lab, D_radiology, D_admin, D_network | the other roles, for the montage |
| U_dial | basic phone with *384*8482# typed |
| U_menu | USSD menu: "VITALIS: healthcare for everyone / 1 Emergency / 2 Not urgent… / 3 Call an ambulance / 4 My last request" |
| U_emergency | "What is happening?" list |
| U_area | "Where are you? (LGA)" list |
| U_sent | "Sent to Abeokuta Central Hospital (2 km)… They will SMS you. Ambulance: 08112000033" |
| D_ussd | hospital Incoming card: "Dialled by USSD, no app or data · Call back 0000 000 0060" with Accept |
| U_sms | SMS inbox: "Abeokuta Central Hospital is ready for VT-… Ambulance: 08112000033…" |

## 3. What to make

- A **2 minute 12 second**, 16:9 film: 1920×1080, 30 fps.
- **Completely silent.**
- A presenter speaks live in front of it.

The story is one woman and one night, then everyone VITALIS reaches. At 2:07 AM she is 34 weeks pregnant and
bleeding. VITALIS takes her from "something is wrong" to "a hospital is ready for you". Then it shows how VITALIS
reaches everyone:
- the ambulance;
- no signal;
- a basic phone with no data (USSD);
- the chemist, her own record, the doctor, consent, and cost.

The viewer must remember four things:
1. three taps;
2. a hospital that is ready for her;
3. it works with no signal;
4. it works on any phone.

The theme is **healthcare for everyone**.

## 4. Scenes

Times are fixed. Each line gives the start time, the text on screen, and the picture.

| Start | On-screen text | Picture |
|---|---|---|
| 0:00 | 2:07 AM. / 34 weeks pregnant. Bleeding. | Near-black. A giant white clock fades in, then the grey subline. |
| 0:06 | Which hospital can actually help her? | White. Three demo hospitals in a column, each struck through with a grey reason under it: Ibara Family Clinic (no obstetrician on duty), Lafenwa General Hospital (obstetrician: unknown), Ogun Teaching Hospital (updated 12 hours ago). |
| 0:12 | VITALIS / Healthcare for everyone. | Near-black. The icon lands in the centre, the wordmark reveals letter by letter, then the line in mint. |
| 0:16 | Three taps. / No account. No typing. | White. P_home: tap "Pregnancy problem". P_body: tap the pelvis. P_symptoms: tap "Heavy bleeding". Then P_emergency. A big counter (1, 2, 3) ticks beside the phone. |
| 0:24 | Only hospitals that can treat her. | Slow push-in on P_emergency's first hospital card (Ready). Tap "Send to this hospital", then cut to P_waiting. |
| 0:29 | The hospital says yes before she arrives. | D_incoming on the left: the cursor clicks Accept. Match-cut to P_accepted on the right. A lock-screen notification slides down: "VITALIS - Abeokuta Central Hospital is ready for you." |
| 0:36 | Help, one tap away. / Ogun State Ambulance · 0811 200 0033 | P_emergency_amb. Push in on the "Call ambulance" button under Call 112. A soft touch dot taps it. |
| 0:41 | No signal. / Still works. | Near-black. The two lines reveal. P_offline rises in from the right; push in on "No signal", then on the NHIA and free maternal care badges. |
| 0:48 | Saved now. Sent when the signal returns. | White. P_saved on the left, then P_sent slides in on the right. A thin mint line joins them. |
| 0:54 | The hospital keeps working too. | D_outbox on a white card. Push in on the top bar "No signal · 1 saved on this phone…". |
| 0:59 | No smartphone. No data. / Still covered. | Near-black. The lines reveal on the left. U_dial on the right, then a crossfade to U_menu. |
| 1:05 | Dial. Choose. Sent. | White. Three basic phones in a row, each appearing in turn: U_emergency, U_area, U_sent. A mint line draws between them. Push in on "They will SMS you". |
| 1:13 | The hospital answers by SMS. | D_ussd card on the left: push in on "Dialled by USSD", then the cursor clicks Accept. U_sms slides in on the right; the top message ("…is ready for…") gets a soft green highlight. |
| 1:20 | The chemist on the corner. / Now the front door. | P_worker, then a crossfade to P_month. Push in on the three numbers. |
| 1:26 | Her history, in her hands. | P_addrecord, then P_record2. Push in on "Reported by you". |
| 1:33 | AI suggests. The doctor decides. | D_safety: push in on "Do not give Hydrochlorothiazide". Then the D_prescribe card slides up. |
| 1:40 | Her record opens only when she says yes. | P_request (tap Allow), then P_wholooked, then P_share. |
| 1:47 | Where her cover works. / NHIA (formerly NHIS). Free maternal care. | D_coverage card on white. Partner tone only, with no NHIA logo. |
| 1:53 | Nine roles. One journey. | Montage of D_reception, D_lab, D_radiology, D_admin and D_network on white cards, 0.8 s each. End on a still grid of the five. |
| 1:58 | 3 taps. 2G. 0 fees. | Near-black. Three big numbers appear one at a time, each with a grey label: "to an emergency plan", "is all USSD needs", "per referral". |
| 2:03 | From "something is wrong" / to "a hospital is ready for you." | White. The words appear one by one; the second line is green. |
| 2:07 | VITALIS / Healthcare for everyone / vitalis.olamide.cloud | Near-black end card. The icon comes up from below and the wordmark wipes in. Small grey line: "Any phone: dial *384*8482# (demo code)". Hold to 2:12. |

## 5. Look and rules

**Colour**
- Near-black #0B1110 for statement scenes.
- White #FFFFFF and light grey #F5F5F7 for product scenes.
- Brand green #0F6E55.
- Mint #6FD6AE is the only accent on dark scenes.
- Ink #1D1D1F for text; grey #6E6E73 for secondary text.
- Red #B42318 only where the app itself shows danger. Never a red screen.

**Type**
- IBM Plex Sans only.
- Titles bold, 80–110 px, left-aligned, revealed word by word, then still.
- At most 8 words of title per scene, plus an optional grey subline. The presenter does the talking.

**Screens**
- Screenshots fill at least 45% of the frame.
- Motion is smooth, eased, 0.5–0.7 s, with slow push-ins.
- Soft grey touch dots for taps; a large cursor for desktop clicks.
- Hold every scene still for at least 1.5 s after its last move.

**Never use:** glows, particles, gradients, tilted 3D phones, lens flares, invented screens, invented numbers, or sirens.

**No audio:** no narration, music, effects or audio track. Export without an audio stream.

**NHIA:** show the NHIA (formerly NHIS) as a partner, never as a problem. No NHIA logo. VITALIS is not affiliated
with the NHIA.

**Numbers:** every number on screen comes from this brief or from the screenshots. The USSD code is a demo code,
so it is labelled that way on the end card.

## 6. How to work

1. Read `/hyperframes`.
2. Unzip the assets as in section 2.
3. Scaffold a project at `~/Downloads/vitalis/v2/film-silent/` and copy in the `brand/`, `fonts/` and the
   `screens/` you use.
4. Build one sub-composition per scene. Each scene's `data-start` must equal its time in section 4.
5. Run `npm run check` and fix every error.
6. Take snapshots 1 s after every scene start (`npx hyperframes snapshot --at 1,7,13,…`) and look at each frame:
   text readable, nothing cut off, screens sharp, nothing overlapping.
7. Render to **`~/Downloads/vitalis/v2/VITALIS-film-silent.mp4`**.
8. Verify with `ffprobe`: the duration is 2:12 (±0.5 s), the video is 1920×1080 at 30 fps, and there is **no audio
   stream**.
9. Report the output path, its duration, and the snapshot frames you checked.
