# USSD: healthcare for everyone

Most people in rural Nigeria have a basic phone, little or no data, and no smartphone. VITALIS works for them by
USSD: they dial a code, answer numbered menus, and the nearest hospital that can treat them gets the request on its
Incoming screen. The hospital's answer reaches them by SMS.

## What they see

```
*384*8482#
VITALIS: healthcare for everyone
1 Emergency
2 Not urgent: find a clinic
3 Call an ambulance
4 My last request
```

- **Emergency**: what is happening (the same eight emergencies as the app) → for pregnancy or a sick child, what they
  see → their local government area → **sent**. Three or four answers.
- **Not urgent**: the problem → who is sick → their area. If it needs a hospital today it is sent; otherwise they get
  the nearest clinic and its number.
- **Call an ambulance**: Ogun State Ambulance, 08112000033, and 112.
- **My last request**: whether the hospital has answered, and its number.

`0` goes back, `00` goes to the start. Every screen fits in 182 characters. A basic phone has no GPS, so they pick
their LGA and VITALIS uses its centre for matching.

## What happens behind it

The answers become the same taps the app sends (`app/services/ussd.py`), so the same red-flag rules, care types and
matching decide. The request is a normal referral with `channel = "ussd"`: the hospital sees **Dialled by USSD**
and a number to call back, and accepts or declines as usual. Accept or decline sends an SMS (with the hospital's
number and the ambulance line). One open request per phone for two hours: dialling again shows its status instead of
alerting another hospital. If no hospital near their LGA can take the case, they are told to call the ambulance.

## Going live

1. Get a USSD code from an aggregator licensed by the NCC (for example Africa's Talking). A shared code like
   `*384*xxxx#` is quickest; a dedicated short code takes longer and costs more.
2. Set the callback URL to `https://<your domain>/api/v1/ussd?key=<secret>`.
3. On the server set `USSD_SECRET=<secret>` and `USSD_CODE=<the code>`, and a real SMS provider
   (`SMS_PROVIDER=termii` or `bulksmsnigeria`) so answers reach people. Then `./deploy/deploy.sh`.
4. Until then, the website's simulator at `/ussd` shows the whole flow with demo numbers (`0000 000 0xxx`) whose
   texts are kept on the server and shown on the page, never sent.

## Emergency numbers

`backend/data/emergency_lines.json` lists 112 and the state ambulances. The ambulance shown is the one for the state
of the nearest known LGA (`backend/data/lgas.json`) within 40 km, so a phone outside a covered state is never shown a
wrong number. To cover another state, add its LGAs (with `"state"`) and its ambulance.
