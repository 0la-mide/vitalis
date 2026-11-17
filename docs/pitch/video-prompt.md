# VITALIS — 60-second pitch video (motion graphics prompt)

Make a 60-second, 16:9 (1920×1080, 30 fps) motion-graphics pitch film for **VITALIS**, a healthcare coordination
platform for Nigeria built for the ITDC 2026 hackathon. Tone: calm, confident, human. It should feel like help
arriving, not like an alarm. Clean flat motion design with real product UI shown inside phone and laptop frames.

## Look and feel
- **Palette:** deep clinical green `#0F5C4A` (brand), calm blue-teal `#134E5E` (emergency surfaces), mint `#EEF6F3`,
  paper `#F6F8F7`, ink `#14201C`. Red `#B42318` only as tiny signals (a dot, an underline), never a full screen.
- **Type:** IBM Plex Sans (bold for headlines, regular for captions). Big, short on-screen words.
- **Motion:** smooth eases, soft depth, gentle parallax. Phone screens slide in and tap with a small ripple. Map
  lines draw on. One recurring motif: a heartbeat line that turns into a route on a map.
- **Music:** warm, minimal piano/pads over a soft pulse, building gently from 0:12 and resolving at 0:55. No sirens.
- **Sound design:** soft tap clicks, one notification chime at the hospital acceptance, a single heartbeat at the open.

## Assets (real screenshots, synthetic demo data)
Phone screens (portrait): `backend/app/guide/img/p1_home.jpg`, `p2_body.jpg`, `p3_symptoms.jpg`, `p4_emergency.jpg`,
`p5_waiting.jpg`, `p6_accepted.jpg`, `p7_record.jpg`, `p8_share.jpg`, `w1_worker.jpg`.
Laptop screens (landscape): `h1_incoming.jpg`, `h2_ai.jpg`, `h3_models.jpg`, `h4_prescribe.jpg`, `h5_lab.jpg`,
`a1_verify.jpg`. Place them in simple device frames; crop/zoom to the part named in each scene.

## Storyboard and voice-over

| Time | Visual | On-screen text | Voice-over |
|---|---|---|---|
| 0:00–0:05 | Dark room, a phone lights up at 2:07 AM. A single heartbeat line crosses the screen. | 2:07 AM | "It's two in the morning. She's pregnant, and she's bleeding." |
| 0:05–0:12 | Top-down map of Abeokuta. The nearest hospital pin pulses, then greys out (no obstetrician on duty). Two more pins flicker: "closed?", "full?". A clock ticks in the corner. | Which hospital can actually help? | "The family has one question: which hospital can actually help, right now?" |
| 0:12–0:22 | Phone: `p1_home` → tap **Pregnancy problem** → `p2_body` → tap groin → `p3_symptoms` → tap **Heavy bleeding** → `p4_emergency` (calm teal banner). A counter in the corner: 1, 2, 3 taps. The bottom bar animates: "8 nearby · 4 can handle this · 2 ready now". | 3 taps. No typing. | "With VITALIS, it takes three taps. No typing, no account. Every tap narrows the hospitals that can really treat her, and danger signs go straight to an emergency plan." |
| 0:22–0:30 | Split screen. Left: laptop `h1_incoming`, the new referral card slides in live. A doctor's cursor taps **Accept**. A soft chime. Right: phone `p5_waiting` flips to `p6_accepted` ("Go now. They are ready for you."). A lock-screen notification drops in: "Hospital is ready". | Accepted in seconds | "The hospital sees her coming before she arrives. One tap to accept, and her phone says: go now, they're ready for you. Directions, what to bring, even a text if her phone is off." |
| 0:30–0:37 | Map zooms out: a chemist shop icon lights up, `w1_worker` on a phone. A dotted line draws from the shop to the hospital. Small vitals (BP, SpO2) float up and travel along the line. | The chemist on the corner, connected | "Most people see a chemist first. VITALIS turns that chemist into the start of the journey, with vitals that travel ahead to the hospital." |
| 0:37–0:47 | Laptop: `h2_ai` zooms to the safety alert: "Do not give Hydrochlorothiazide… allergy recorded at Ogun Teaching Hospital." Then `h4_prescribe` shows the block. Captions highlight "recorded at another hospital". | AI suggests. The doctor decides. | "At the bedside, VITALIS AI reads her history across hospitals, flags red signs, and stops a medicine that clashes with an allergy recorded somewhere else. It suggests; the doctor decides." |
| 0:47–0:54 | Phone: `p8_share` QR code pulses; it scans onto the laptop and a lock icon opens. Then `p7_record` with a "Who looked" list sliding in. | Her record. Her choice. | "Her records only open when she says so, by QR or one tap, and she can see every person who looked." |
| 0:54–1:00 | Heartbeat line becomes a calm route line that ends at a hospital icon with a check mark. Logo **VITALIS** in brand green on paper. | From "something is wrong" to "a hospital is ready for you." vitalis.olamide.cloud | "VITALIS. From 'something is wrong' to 'a hospital is ready for you.'" |

## Voice
Warm Nigerian English, calm and unhurried, mid-30s, about 140 words in total. Leave half a second of silence
after "she's bleeding" and after "they're ready for you".

## Rules
- Use only the real screenshots and the features listed; do not invent features or statistics.
- Keep all patient details synthetic (as in the screenshots). No real names, faces or hospital logos.
- Never show a disease name on the patient's phone; the AI is decision support, not a diagnosis.
- End card must stay on screen for at least 3 seconds.
