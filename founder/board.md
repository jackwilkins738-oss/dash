# Board verdict: TicketFlow (working name)

**Vote: 3 FUND IF, 0 FUND, 0 PASS. Average score 4.7 / 10.**
Offers 5 · Monopoly 4 · Product 5. Memos are in `board/`.

## Risks more than one member raised (most dangerous first)

1. **Distribution (all three).** "SEO + communities, no outbound" is the weakest route to owners of 5–20 truck firms. Many don't search for software or spend time in online communities. Nobody can say how the first 25 customers arrive or what each costs to win.
2. **Geography undefined (all three).** "Roll-off" is a US term, the pricing is in GBP, and the UK trade says "skip hire". Market size, search terms, ticket formats and invoicing norms all depend on picking the country.
3. **Drivers and OCR are an unproven weak link (Offers, Product).** The value depends on drivers photographing every ticket and OCR reading faded, thermal or wet tickets. If either fails, overage capture fails quietly and the main promise breaks.
4. **Pain not yet quantified (all three).** "Unbilled overages" is the founder's account so far, not a measured figure per operator.
5. **Easy to copy / no moat (Monopoly; Offers via the "commodity app" framing).** The product is commodity OCR plus Stripe, and existing hauling software could add the feature. Competitors are an open question.

## Where the members disagree
- **Scope.** Product wants job intake and driver assignment **cut** (it's dispatch software, and it slows the first five minutes). The other two didn't object to the scope and called it narrow.
- **Price.** Offers thinks £79–£149 is probably **underpriced** if the overage recovery is real, and wants it priced against money recovered with a guarantee. Monopoly worries about the reverse: at that price, acquisition cost must be tiny.
- **Moat.** Only Monopoly scored the lack of durability as a top-3 killer. Product and Offers care more about whether it works on day one.

## Conditions checklist (merged)

Before any serious code:
- [ ] Pick the country and the trade's own vocabulary; estimate the number of target operators. → `/founder-competitors`
- [ ] Map existing tools these operators use, and find out whether any already captures scale tickets. → `/founder-competitors`
- [ ] Run OCR on real scale tickets from several disposal sites; hit a stated accuracy target, with a fast manual-correction path.
- [ ] Of the 20 conversations, **≥5 pay the £99 pilot**, with the source and acquisition cost recorded for each. → `/founder-consumer` (simulated), then real
- [ ] **≥3 operators document real unbilled overages** from past tickets, clearly above the subscription price. → `/founder-cfo`

Offer and product:
- [ ] Reframe the pitch as recovered revenue, not as a cheaper app; consider a "pays for itself in month one or free" guarantee. → `/founder-offer`, `/founder-pricing`
- [ ] Cut the MVP to capture → read → flag → send. Drop job intake and driver assignment; bring in quote terms by a short form or an import.
- [ ] Attach the ticket photo to every overage invoice as proof.
- [ ] Get records into the owner's existing books without re-keying, export at minimum, before charging.
- [ ] Pilot proves driver adoption: 2+ fleets, several weeks, high capture rate without the owner chasing drivers.

Go-to-market and durability:
- [ ] Allow direct outreach (calls, yard visits) for the first cohort.
- [ ] State one credible moat route within 24 months (site-level ticket and fee dataset, disposal-site integrations, or regional category ownership).

## The strongest version the board can see

This is not "a cheaper app for haulers". It is **a revenue-recovery tool for one country's skip/roll-off operators**. The driver photographs the ticket, the ticket photo is attached as proof, the overage is billed, and the owner's books get the record. It is priced against the money it recovers and backed by a guarantee. It is sold to the first 25 customers by phone and yard visits, and SEO and communities come later, once there are case studies to rank and share. It starts without dispatch features at all. If the pilot can't show real recovered overage above the subscription price, the right answer is to stop, not to add features. That differs from the pitch in three ways: narrower scope, higher price framing, and founder-led sales at the start.
