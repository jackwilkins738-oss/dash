# Competitors: UK skip hire, ticket-to-invoice

Researched 2026-10-16. **Method caveat:** this environment's network policy blocked opening vendor sites directly, so every fact below comes from web-search result snippets of the linked pages, not from pages I read in full. Treat prices as "reported", and check them on the live pages before relying on them. Nothing here is invented. Where a search turned up nothing, the entry says "not found".

Note: `founder/idea.md` now targets **UK skip hire**.

## 1. Who is there (most direct first)

| Competitor | Type | Price (comparable tier) | What overlaps with your MVP |
|---|---|---|---|
| [SkipDesk](https://www.skipdesk.co.uk/) | Direct | **£79 / £99 / £149 per month** | VAT invoices, **Stripe payment links**, DEFRA-compliant waste transfer notes (WTNs) on every tier. Same price points as your plan. |
| [SkipRoute](https://skiproute.co.uk/) | Direct | £99 (≤3 vehicles) / **£199 (≤10)** / **£349 (≤25)** / £499, ex VAT | Driver app, photo proof, digital job sheets capturing **tip-ticket and weighbridge references**, Xero/QuickBooks/Sage. |
| [weighzIO](https://weighz.io/) | Direct | not found | Driver app records **weights**, load breakdowns and signatures; photos attached to the ticket. |
| [SkipPlanner](https://thebridgegroup.uk.com/skipplanner/) | Direct | not found | Digital tickets with **photographs and weighbridge information**; driver app. |
| [Skip Tracker](https://www.skiptracker.co.uk/) | Direct | £49 + VAT/mo, ≤10 users (one snippet; unconfirmed) | Tracking and invoicing. |
| [SkipLogic](https://www.skip-logic.app/) | Direct | not found; 30-day free trial | Aimed at independent operators. |
| [Cloudskip](https://cloudskip.co.uk/) | Direct | not found | Scheduling, automatic invoices, tracking of outstanding payments. |
| [Skip Office](https://skipoffice.co.uk/) | Direct | not found | Invoicing; images and documents uploaded per ticket. |
| [Access Weighsoft](https://www.theaccessgroup.com/en-gb/waste-management/software/skip-hire-management/) | Direct, enterprise | [Request pricing](https://www.theaccessgroup.com/en-gb/waste-management/access-weighsoft-pricing/) | Full suite, driver app, Digital Waste Tracking compliance. |
| [Midsoft SkipTrak](https://www.midsoft.co.uk/product/skiphiresoftware/) | Direct, legacy | Drivers App £900 + yearly support | Weighbridge tickets; customer portal for checking tickets against invoices. |
| [Routeware UK](https://uk.routeware.com/skip-hire-software) | Indirect (bigger fleets) | not found | Billing, payments, driver tools. |
| [fissara](https://www.fissara.com/waste-management-software/skip-hire-management-software/) | Indirect | not found | Generic field-service tool set up for skip hire. |
| Paper tickets + Excel + Xero/QuickBooks/Sage | Substitute | £0 extra | The status quo you're replacing. |
| Generic receipt-OCR tools | Substitute | not checked | Not skip-specific; no comparison against the quote. |

## 2. Price range (self-serve, comparable small-fleet tier, per month)
- **Lowest:** £49 (Skip Tracker, unconfirmed)
- **Median:** about £99–£149 (SkipDesk's tiers; SkipRoute's entry tier)
- **Highest published:** £349 for ≤25 vehicles, £499 for unlimited (SkipRoute). Enterprise suites quote on request.
- **For a 5–20 vehicle fleet specifically:** SkipRoute charges £199–£349. **Your planned £79–£149 sits at or below the cheapest full suites**, which already include scheduling, WTNs and invoicing.

## 3. Positioning map

Axes: **scope** (point tool ↔ full operations suite) × **price** (cheap self-serve ↔ quote-only enterprise).

```
                  full suite
                      |
   SkipDesk  SkipRoute |  Access Weighsoft
   SkipLogic Cloudskip |  Routeware
   Skip Office         |  Midsoft
   SkipPlanner weighzIO|
cheap ----------------+---------------- enterprise
                      |
   YOUR PITCH         |
   (ticket→invoice    |
    only, £79–£149)   |
   Paper + Xero       |
                  point tool
```

You'd be the only point tool, priced like a full suite.

## 4. Complaints (what their customers say)

**Not enough evidence to rank complaints.** Searches found no independent reviews of SkipDesk, SkipRoute, Cloudskip, Skip Office or SkipLogic on Capterra, G2 or Trustpilot. The only data point:
- Access Weighsoft: [Capterra UK](https://www.capterra.co.uk/software/1021876/isys-weighsoft) gives it 3.8/5 for value from **4 reviews**. One reviewer described the initial setup as poor. **Thin** (fewer than 3 reviews make this point).

Vendor blogs describe the pain you're targeting, which confirms it exists but isn't independent evidence. SkipRoute's [job-sheet article](https://skiproute.co.uk/blog/skip-hire-job-sheet-software) calls matching "a driver's handwriting with customer records, tip tickets, and invoices" "a daily headache". Its [accounting article](https://skiproute.co.uk/blog/skip-hire-accounting-software) says manually matching tip-site invoices to jobs is "a nightmare". The founder's own 20 conversations are the real source; `/founder-consumer` can only simulate it.

## 5. The gap

**The broad gap you pitched mostly doesn't exist.** At least four UK products already do the following from a phone: capture weighbridge or tip-ticket data, attach photos, and turn jobs into invoices. SkipDesk does Stripe payment links at your exact price points.

**What I found no evidence of anyone claiming:**
1. **OCR of the paper tip ticket.** Competitors have drivers *type in* the weight or reference, or photograph the ticket as an attachment. None says it *reads* the ticket automatically.
2. **Automatic overage detection against the quote,** i.e. "this skip was 1.4 t over its limit; here's the surcharge line, with the ticket photo as proof".

That is a **feature-sized gap, not a product-sized one**. It's also smaller in the UK than in US roll-off. UK skips are usually sold at a flat price with a weight limit. Aggregator guides put overweight surcharges at about [£30–£120 per tonne over a 4–7 t limit](https://www.bizhub365.com/find/skip-hire/havering/cost/), varying by town. Missed surcharges are real money but modest per job; the CFO needs to size them.

**The bigger force is regulation.** [Defra digital waste tracking](https://www.circularonline.co.uk/news/mandatory-digital-waste-tracking-rollout-delayed-by-six-months/) becomes mandatory for receiving sites from October 2026, and **for carriers (which includes skip hire operators) from October 2027**, with a voluntary public beta in spring 2027. Confirm this on gov.uk. Every small operator will need software that reports waste movements. A ticket-to-invoice tool *without* digital waste tracking support will look like a second app owners have to pay for. A tool *with* it is a must-buy, but that's a full suite, and you'd be competing head-on with the list above.

**So the gap you can own is one of these:**
- **(a) A feature others license.** Sell "tip-ticket OCR + overage detection" as an add-on or API to SkipDesk, SkipRoute and the others, or to operators already on them. That's a small but real business, and it needs no sales channel to operators.
- **(b) A digital waste tracking-first suite for 5–20 vehicle operators,** with OCR and overage recovery as the differentiator. This is a much bigger build, in a crowded field, against a 2027 deadline every competitor is also racing.
- **(c) Neither.** If operator conversations show surcharges are rarely missed, there's no gap.

## 6. The threat

**Who can copy you fastest:** SkipRoute and weighzIO. Both already have driver apps that capture weighbridge data. Adding "read the ticket photo with an off-the-shelf OCR/AI model and compare it to the job's weight limit" is weeks of work for them. SkipDesk already matches your price and payment flow. If your MVP gets any traction, any of them can ship the same feature to their existing customers before you reach 25.
