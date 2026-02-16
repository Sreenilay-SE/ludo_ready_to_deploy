# 🛡️ ExitGuard – Stop Users From Rage-Quitting Your Site

ExitGuard is a real-time "please don't leave" system.

It watches how people behave on your website/store right now, spots when they're getting annoyed/frustrated/confused, quickly decides how likely they are to bounce, and tries to save them with exactly the right message or offer before they close the tab.

Normal analytics tell you "yesterday 14% of people left".  
ExitGuard tries to stop the 14% while they're still angry-clicking.

---

## What it actually watches (the signals that matter)

- Rage clicks (bashing the same spot 6–10 times in 2 seconds)
- Dead clicks (clicking on things that do nothing — logos, headlines, empty space)
- Super long hovers on buttons ("should I… should I not…")
- Mouse wiggling / frantic small movements
- Long idle periods suddenly after being active
- Weird scrolling patterns (up-down-up-down very fast)

From those it guesses the mood:

- 😣 Frustrated
- 🤔 Confused
- ⏳ Hesitating
- 😐 Neutral / 😊 Flowing nicely

---

## How serious is the danger? (0–100 Risk Score)

We throw all the signals into a pretty straightforward but tuned scoring system:

- 0–30   → green, they're fine
- 31–60  → amber, starting to get wobbly
- 61–100 → red, they're emotionally on the way to the close button

When it hits ~65–70+ we trigger something:

- Small discount / free shipping popup for cart abandoners
- "Looks like you're stuck — want to chat?" bubble
- Help overlay / quick FAQ for confused scrollers

---

## The thing I'm most proud of: Salvage Rate

Instead of just "conversion rate went up 0.8%", we actually track:

**Salvage Rate** = % of "red zone" people who ended up buying after we intervened  
**Revenue Saved** = actual ₹ / $ we think we rescued in that time window

Feels way more real than vanity uplift percentages.

---

## Tech (kept it intentionally simple & fast)

- Frontend tracking → vanilla JS (no React, no npm hell)
- Backend → Flask + Redis (because sessions need to be lightning fast)
- Dashboard → plain HTML + CSS + vanilla JS fetching data every 4 seconds
- Colors → dark slate + emerald green accent (because I like it)

No mega frontend framework, no 47 dependencies, no 3-second TTI. Goal was: tracking script should feel invisible.

---





---

## Okay, let's see it working (2-minute demo)

1. In one tab: open `dashboard.html` → login admin / admin123
2. In another tab: open `demo-store.html`
3. Do stupid user things:
   - Hammer-click an image 8 times really fast
   - Click paragraph text repeatedly
   - Hover 5 seconds on "Add to Cart" then leave
   - Wiggle mouse like crazy for 4 seconds
4. Watch dashboard:
   - Your session pops up live
   - Mood changes
   - Risk score climbs
   - When it goes red → popup should appear in demo store
5. Finish checkout → see "salvaged!" on dashboard

---

## Local setup (quick & dirty)

Backend
```bash
cd backend
pip install -r requirements.txt
# optional .env file (or just use defaults)
python app.py









