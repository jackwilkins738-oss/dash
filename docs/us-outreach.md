# US outreach

A second, separate outreach workspace for US trades. It runs the same pipeline as the UK one (find
firms, check their sites, preview pages, emails, replies, autopilot) but works in its own folder,
`outreach-us/`, with its own settings, inboxes and lists. Nothing in it can reach the UK lists, and
the UK can't reach it.

**Double-click `scripts/control_panel_us.bat`.** It opens on http://127.0.0.1:8766, with "· US" in
the title, beside the UK panel on 8765.

---

## What's different in the US workspace

| | UK | US |
|---|---|---|
| Finding firms | Google Maps or Companies House | Google Maps only (US search words; Home Depot, Angi, Roto-Rooter and similar left out) |
| Areas | `Guildford, GU1` | `Provo, UT; Ogden, UT` - the state stays with its city |
| Who can be emailed | Ltd / LLP only (PECR) | Any business (CAN-SPAM) |
| No email | A letter | Not contacted - no letters |
| Every email must have | - | Your postal address (`{{postal_address}}`) and a way to opt out |
| Prices | £750 / £2,500 | $1,500 / $4,500 |
| Dashboard after its free year | £39 a month | $59 a month (`lib/market.ts`, `scripts/workspace.py`) |
| Online quotes | Yes (dashboard) | No - the dashboard's are pounds + UK VAT + UK terms. Send the price in a reply |
| Preview page | scalardigital.co.uk | The US domain: dollars, no UK phone or WhatsApp, "call" not "ring" |

## Before the first US email

1. **Buy the US domain** and add it to this Vercel project (Settings → Domains), so preview pages
   load on it.
2. **Vercel → Environment Variables:** `US_SITE_HOSTS` = the domain, with and without www
   (`scalardigital.com,www.scalardigital.com`). Redeploy. A preview opened on that host shows the
   US version. To check one before then, add `?m=us` to any preview link.
3. **US panel → Settings:**
   - `SITE_URL` - the US domain (so every link in a US email is on it)
   - `POSTAL_ADDRESS` - a real address. **US sending won't start without it.** A virtual mailbox
     is fine.
   - `MAIL_ADDRESS` and the extra inboxes - **new inboxes on the new domain**, warmed up for 3-4
     weeks before outreach, the same as any new inbox
   - `BOOKING_LINK`, `GOOGLE_PLACES_API_KEY`, `PAGESPEED_API_KEY`, `PROSPECTS_API_SECRET`,
     `DASHBOARD_API_URL`, `ANTHROPIC_API_KEY` - the same values as the UK panel
   - `QUOTE_PRICE_BUILD` / `QUOTE_PRICE_LANDING` - leave blank for $4,500 / $1,500
   - **Telegram: leave blank, or use a second bot.** Two panels can't share one bot - they'd fight
     over its messages.
4. **Autopilot:** set its time for US mornings - Utah is 7 hours behind the UK, so 14:00-16:00 UK
   time lands at 7-9am there. It's a separate Windows task ("Scalar Prospect Autopilot (US)"), so
   it never replaces the UK one.
5. **Mailmeteor:** if you send US batches through Mailmeteor instead of the panel, its templates must
   carry your postal address and an opt-out line too. The panel's own sending checks this; Mailmeteor
   can't.

## Not done yet

- **No showcase scene for plumbing, electrical or HVAC.** The preview's concept site falls back to
  the driveways design for those trades (true in the UK too). Until there are scenes for them, the
  best-matching US trades are roofing, landscaping, concrete and general contractors.
- **Online quotes and payment in dollars** need the dashboard (a separate repo) to support USD with
  no VAT, and US terms of business.
