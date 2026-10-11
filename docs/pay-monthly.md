# Pay monthly

The same build, nothing upfront: 12 monthly payments from the day the site goes live, then it's theirs
outright. Each payment is the one-off price / 12, rounded down to whole pounds (or dollars), so the total is
never more than paying at once and there's no interest or fee.

| | One-off | Pay monthly |
|---|---|---|
| UK Scalar build | £2,500 | 12 x £208 (£2,496) |
| UK landing page | £750 | 12 x £62 (£744) |
| US build | $4,500 | 12 x $375 |
| US landing page | $1,500 | 12 x $125 |

Where it shows: preview pages (both prices on every card, a "Can I pay monthly?" answer), the homepage
pricing cards, the first email (UK and US), the "How much?" saved reply, and what AI reply drafts are told.
On the Calls tab, tick **pay monthly** before pressing a Quote button: the quote and proposal carry the
pay-monthly terms (terms.py) and a `payment_plan` for the dashboard.

## Why exactly 12 payments, with nothing added

Many trades are sole traders, and in the UK spreading a price for a sole trader can be regulated consumer
credit. The exemption relied on here is credit repaid in **12 or fewer payments, within 12 months, with no
interest or other charge**. So: never more than 12 payments, never a total above the one-off price, never a
late fee. Have an accountant or solicitor confirm this once before relying on it. Limited companies, and US
businesses, aren't affected.

## Taking the payments (set up once)

The dashboard doesn't collect instalments yet, so for now:

1. **Stripe** (or GoCardless for Direct Debit): make a product per plan - "Scalar build, pay monthly" at £208 a
   month, "Landing page, pay monthly" at £62 a month.
2. When a pay-monthly quote is accepted and the site is ready to go live, send a subscription link that
   **ends after 12 payments** (Stripe: a subscription schedule with 12 iterations, or `cancel_at` 12 months on).
   First payment on launch day.
3. Turn on Stripe's automatic retries and failed-payment emails.
4. Paying off early: cancel the subscription and send one invoice for what's left.

## Hosting until it's paid off

Pay-monthly sites are hosted on **your** Cloudflare account until the last payment (one-off sites go straight
on a free account in the client's name). The domain is in the client's name from day one.

- After the last payment: move the Pages project to a free Cloudflare account in their name and point their
  domain at it. Tell them it's theirs.
- **Missed payment** (terms.py, "If a payment is missed"): tell them straight away; a written reminder 14 days
  after it was due; if still unpaid 14 days after that, the site can go offline - deploy a simple "back soon"
  page to the project - until they're up to date, then redeploy the site. Never add a fee for paying late.
- **They stop**: pay off the rest and it's theirs, or the site comes down at the end of the last month paid.
  Their domain stays theirs either way.
