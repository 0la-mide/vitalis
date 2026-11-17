GOAL:    a judge remembers "three taps and a hospital that is ready for her", and sees every key feature working
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps
TIME:    60 s x 30 = 1800 frames; no music yet (bed to add), sound effects on visible actions
LOOK:    the app's own system. Ground paper #F6F8F7, hospital world mint #EEF6F3, night world calm teal #134E5E,
         reveal/end world brand green #0F5C4A. Ink #14201C, muted #4B5A55. Accent = brand green on one element per
         shot (the tap counter, the NHIA underline, the mark). Red #B42318 only as the app shows it.
         Type IBM Plex Sans: titles 72-88 px 700, -2% tracking, left aligned; subs 34 px 500; floor 28 px.
         Medium: real product screens captured at 2x (phone 780x1688, desktop 2880x1800), phone in a #101614 bezel
         (radius 62, 14 px), desktop crops on white cards radius 20; shadow 0 40 80 rgba(20,32,28,.16). No grain.
OBJECTS: her phone (real screens), the browser's own permission sheets (location, notifications), the hospital's
         Incoming card with Accept, the doctor's safety alert, the lab worklist, the reception Patient details card
         (name, VITALIS ID, NHIA formerly NHIS), the brand icon file.
MOTION:  arrivals expo.out 0.5-0.6 s; camera power2.inOut 0.6 s; exits power3.in, 40% shorter; titles per word
         blur 6->0 in 0.13 s, 0.067 s apart, then dead still; screen swaps = blur swap 0.15 s; taps = a soft touch
         dot (press 0.12 s), no rings; cursor 64 px, moves 0.6 s power2.inOut.
SHOTS:   0-4.5 night: "2:07 AM", she is 34 weeks pregnant and bleeding -> teal floods to paper
         4.5-9.5 the old way: "Which hospital can actually help?", three real demo hospitals struck through -> green rises
         9.5-12.5 reveal: icon, VITALIS, "Get the right hospital, fast" -> floods to paper
         12.5-22.5 three taps: counter 1-2-3; location sheet; emergency plan; punch-in on the matched hospital; send
         22.5-29 the hospital clicks Accept -> match cut to her phone; notification permission; "Hospital is ready"
         29-36 the chemist starts it too; reception: one VITALIS ID, her name, her NHIA (formerly NHIS) number
         36-44.5 doctor: AI safety alert from another hospital's record; prescribing blocked; "AI suggests"
         44.5-48.5 lab and radiology worklists; "Sample collected"
         48.5-54.5 consent: Allow / Don't allow; who looked; QR once for 10 minutes
         54.5-60 montage (dark mode, verification, shared record) -> claim -> mark, URL, hold 1.5 s
BANNED:  dark void with floating UI; glow, particles; purple/blue gradients; glass cards; cream paper with serif;
         three cards in a row; title over a dimmed screenshot; docked logo; click rings; UI tilted in 3D;
         drawn mockups of app screens (only the browser's permission sheets are drawn); invented numbers.
QA:      t=2 night title readable; t=7 three struck rows; t=11 mark; t=17.3 counter 3 + emergency plan;
         t=24.4 cursor on Accept; t=26.5 notification on her phone; t=33.5 NHIA card; t=39 safety alert readable;
         t=46.5 lab click; t=51 who looked; t=58.5 end card.
