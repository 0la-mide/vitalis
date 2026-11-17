# VITALIS pitch film: production brief

Everything needed to make the film: script, timing, visuals, voice, music, sound and brand.
Assets are in `VITALIS-video-assets.zip` (real app screens, icon, fonts).

---

## 1. The film in one line

One woman, one night: at 2:07 AM she is 34 weeks pregnant and bleeding. VITALIS takes her from
"something is wrong" to "a hospital is ready for you", and on the way shows every key feature of the app.

**The one thing a viewer must remember:** three taps, and a hospital that is ready for her.

## 2. Specs

| | |
|---|---|
| Length | 60–62 seconds |
| Format | 16:9, 1920 × 1080, 30 fps, MP4 (H.264 + AAC) |
| Also useful | a 9:16 vertical cut (1080 × 1920) for social |
| Loudness | about -16 LUFS integrated, true peak below -1 dB |
| Data | every person, hospital and record shown is **synthetic demo data** (say so on the end card) |

## 3. Voice

- **Voice:** Davis (VibeVoice-Realtime, voice `en-Davis_man`, model `mlx-community/VibeVoice-Realtime-0.5B-8bit`).
- **Delivery:** calm, warm, unhurried, confident. Not dramatic, not salesy. About 2.6–3.0 words per second.
- **Pauses:** half a second after "and bleeding." and after "This is VITALIS."
- **Pronunciation:** VITALIS = "vee-TAH-lis". NHIA = "N-H-I-A" (letters). NHIS = "N-H-I-S".

## 4. Script with timing

Times are when each line starts in the film. The narration never reads the on-screen titles word for word.

| # | Start | Voice-over (Davis) | On-screen text | Visual |
|---|---|---|---|---|
| 1 | 0:00.5 | Two in the morning. Thirty-four weeks pregnant, and bleeding. | **2:07 AM** · She is 34 weeks pregnant. And she is bleeding. | Calm deep-teal screen (#134E5E), giant white clock "2:07 AM". |
| 2 | 0:04.8 | Her family has one question, and every wrong answer costs time. | **Which hospital can actually help?** | Light screen. Three hospital names appear, then each is struck through: Ibara Family Clinic (no obstetrician on duty) · Lafenwa General Hospital (obstetrician: unknown) · Ogun Teaching Hospital (updated 12 hours ago). Green rises from the bottom. |
| 3 | 0:10.0 | This is VITALIS. | **VITALIS** · Get the right hospital, fast | Green screen (#0F5C4A). App icon lands, wordmark appears letter by letter. |
| 4 | 0:13.0 | She taps what's happening, where it is, and what she sees. That's all it takes. | Big counter **1 → 2 → 3** · "taps to an emergency plan" · "No account. No typing." | Phone (real screens): `P_home` → tap *Pregnancy problem* → browser asks **"Know your location?" Allow** → `P_body` (pregnant figure) → tap groin → `P_symptoms` → tap *Heavy bleeding* → `P_emergency`. Counter rolls with each tap. |
| 5 | 0:18.8 | VITALIS only offers hospitals that can treat her, and they're alerted at once. | **Only hospitals that can treat her** · Matched to the care she needs | Push in on the emergency screen: "Abeokuta Central Hospital — Ready — Has obstetrician on duty, blood available, theatre available". Tap **Send to this hospital** → `P_waiting`. |
| 6 | 0:23.4 | The hospital accepts on its own screen, and her phone tells her to go now. | **The hospital sees her coming** → **Accepted before she arrives** · An alert even when the app is closed | Laptop: `D_incoming` (her referral card with Accept / Decline). Cursor clicks **Accept**. Cut to her phone: browser asks **"Show notifications?" Allow** → `P_accepted` ("Go now. They are ready for you.") + lock-screen notification "VITALIS · Hospital is ready — Abeokuta Central Hospital is ready for you." |
| 7 | 0:29.0 | A chemist on the corner can start the same journey. | **The chemist on the corner can start it too** · Walk-in triage and vital signs | Phone: `P_worker` (chemist's New walk-in screen). |
| 8 | 0:32.2 | Her ID carries her name and NHIA number everywhere. | **One VITALIS ID.** **Her name. Her NHIA number.** · She adds it. Reception can fix it. · NHIA, formerly the NHIS | Light mint screen: `D_details` (Patient details: Name · VITALIS ID · NHIA (formerly NHIS) number), green underline under the NHIA number. |
| 9 | 0:36.2 | At the bedside, the AI finds an allergy written at another hospital, and blocks the clash. | **It remembers what another hospital wrote** · Allergy recorded at Ogun Teaching Hospital | `D_safety`: push in on the red flag and the safety alert "Do not give Hydrochlorothiazide… documented allergy to Sulfonamides (Septrin). Recorded at Ogun Teaching Hospital". |
| 10 | 0:42.05 | But the doctor stays in charge. | **AI suggests. The doctor decides.** · Overriding it needs a reason | `D_prescribe`: "Blocked: conflicts with the record", override needs a clinical reason (audited). |
| 11 | 0:44.0 | Lab and radiology each work their own list. | **Lab and radiology, each with its own worklist** · Verified results go back to the doctor | `D_lab`: cursor clicks **Sample collected**. |
| 12 | 0:48.0 | Nobody sees her history unless she allows it, and she can see who looked. | **Her record opens only when she says yes** → **She sees every hospital that looked** (and can stop it any time) → **Or shares one QR, once** | Phone: `P_request` (Abeokuta Central Hospital wants to see your health record — Don't allow / **Allow**) → tap Allow → `P_wholooked` → `P_share` (QR code, works once, 10 minutes). |
| — | 0:54.0 | *(no voice: music and quick cuts)* | — | Fast montage, about 0.4 s each: dark mode home (`P_home_dark`), verification queue (`D_admin`), records from other hospitals (`D_network`). |
| — | 0:55.3 | *(no voice)* | **From "something is wrong"** / **to "a hospital is ready for you."** (second line in green) | Light screen, words appear one by one. |
| 13 | 0:58.6 | VITALIS. Get the right hospital, fast. | **VITALIS** · vitalis.olamide.cloud · ITDC 2026 · synthetic demo data | Green end card: icon carried in from below, wordmark wipes in, URL. Hold at least 3 seconds. |

**Word count:** about 136 words of narration.

## 5. Features the film must show (checklist)

- [ ] Emergency in **3 taps**, no account (patient home → body map → symptom → emergency plan)
- [ ] Women's body map shows breasts; pregnant woman's figure is pregnant
- [ ] **Permissions:** location (browser), notifications (browser), the patient's own **Allow / Don't allow** for her record
- [ ] Only hospitals that can treat the case are offered; hospitals alerted at once
- [ ] Hospital **Accept** → her phone says **Go now**, with a push alert (and SMS)
- [ ] The chemist (frontline worker) can start a referral
- [ ] One **VITALIS ID** with her **name** and **NHIA number**, seen at reception
- [ ] **VITALIS AI** red flag + safety alert from another hospital's record; prescribing blocked; "AI suggests. The doctor decides."
- [ ] **Lab and radiology** worklists; "Sample collected"; only verified results go back
- [ ] **Consent:** who looked, stop any time, one-time QR (10 minutes)
- [ ] Light and dark mode; admin verification (montage)

## 6. NHIA wording (important)

The NHIA (formerly NHIS) is shown as a **partner, never a problem.**
- Say: "her NHIA number", "NHIA, formerly the NHIS", "works alongside the NHIA".
- Never: anything that suggests the NHIS failed, is slow, or is being replaced.
- VITALIS is **not affiliated with or endorsed by the NHIA**; do not use the NHIA logo.

## 7. Look

| | |
|---|---|
| Brand green | `#0F5C4A` (reveal, end card, accents) |
| Calm teal | `#134E5E` (the 2:07 AM night scene, emergency surfaces) |
| Mint | `#EEF6F3` (hospital scenes) |
| Paper | `#F6F8F7` (light scenes) |
| Ink | `#14201C` (text) · muted `#4B5A55` |
| Red | `#B42318` only where the app itself shows it (danger signs). Never a red full screen. |
| Font | IBM Plex Sans (in the zip). Titles bold, 72–88 px at 1080p, left-aligned, max 6–8 words per line. |
| Icon | `brand/icon.png` (mint cross with heartbeat line on green). Do not redraw it. |

**Style:** calm, clean, premium (Apple-like). Real product screens inside a dark phone bezel or on white cards with a soft
shadow, shown large (fill at least 40% of the frame). Smooth moves (0.4–0.6 s, ease-out), titles appear word by word then
stay still. Taps shown as a soft grey touch dot; desktop clicks with a large cursor.

**Avoid:** dark empty backgrounds with small floating UI, glows and particles, purple/blue gradients, three cards in a
row, the logo stuck in a corner, tilted 3D phones, invented screens or numbers, sirens.

## 8. Music and sound

- **Music:** warm, hopeful, minimal: felt piano, soft strings, a gentle steady pulse, light Afrobeat-inspired
  percussion, major key, about 100 BPM. Builds gently from the reveal (0:10); lifts at the hospital acceptance (~0:26);
  resolves on the end card. Duck it about 10–12 dB under the voice.
- **Sound effects (subtle, under the voice):** soft click on each phone tap · crisp click on desktop clicks ·
  short whoosh on scene changes (vary them) · small pop as the tap counter rolls · one notification chime when
  "Hospital is ready" appears (~0:26) · one soft bass impact as the end-card icon lands (~0:58.4).

## 9. Assets in the zip

`screens/` (real captures of the live app at 2×, synthetic data):

| File | What it shows |
|---|---|
| `P_home.png` | Patient home: "What is happening?" emergency buttons |
| `P_body.png` | Body map, pregnant woman |
| `P_symptoms.png` | "What do you see or feel?" (Heavy bleeding, Labour pains, …) |
| `P_emergency.png` | Emergency plan: Call 112, matched hospitals, Send to this hospital |
| `P_waiting.png` | Waiting for the hospital to confirm (VITALIS ID, map) |
| `P_accepted.png` | "Go now. They are ready for you." directions, what to bring |
| `P_record.png` | My health record with name and NHIA number |
| `P_request.png` | Hospital asks to see her record: Don't allow / Allow |
| `P_wholooked.png` | Who can see your record now / Who looked / Stop |
| `P_share.png` | One-time QR code (10 minutes) |
| `P_worker.png` | Chemist's New walk-in screen |
| `P_home_dark.png` | Patient home in dark mode |
| `D_incoming.png` | Hospital Incoming: her referral with Accept / Decline |
| `D_details.png` | Reception Patient details: name, VITALIS ID, NHIA (formerly NHIS) |
| `D_safety.png` | VITALIS AI: red flag + safety alert from another hospital |
| `D_models.png` | Team's risk models (diabetes, heart) with bands and model score |
| `D_prescribe.png` | Prescribing blocked: conflicts with the record |
| `D_lab.png` / `D_radiology.png` | Lab and radiology worklists |
| `D_network.png` | Records from other hospitals (after consent) |
| `D_admin.png` | Admin verification queue |
| `D_visit.png`, `D_reception.png`, `D_ai.png` | Full visit pages (extra coverage) |

`brand/icon.png` (app icon, 512 px) · `fonts/` (IBM Plex Sans 400–700, WOFF2) ·
`reference/VITALIS-pitch-v1.mp4` (the first cut, for timing reference only).

Drawn elements (not screenshots): the browser permission sheets ("vitalis.olamide.cloud wants to — Know your location /
Show notifications — Block / Allow") and the lock-screen notification. Keep their wording exactly as above.
