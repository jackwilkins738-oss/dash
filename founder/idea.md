# TicketFlow (working name)

- What it is: a mobile-first SaaS that turns a photo of a disposal-site scale ticket into an invoice-ready job record, flags overages against the quoted price, and lets the owner send a Stripe payment link in one tap.
- Who it is for: UK skip hire companies running 5–20 trucks, where the owner currently reconciles handwritten scale tickets by hand (typically every Friday) and chases missing paperwork.
- What it sells, at what price: a monthly subscription, £79–£149/month self-serve, 14-day free trial. Validation offer before build: a £99 pilot.
- Where and how: UK only, online, self-serve. Customers found through SEO and roll-off operator communities; no personal/outbound sales. Drivers use it on their phones at the disposal site; owners use it to review and invoice.
- Budget and constraints: validate first (20 operator conversations + £99 pilot) before writing serious code. Narrow MVP: job intake, driver assignment, photo capture, OCR extraction, overage flagging, one-tap invoicing. Stack Next.js + Supabase + Stripe + Vercel, under £50/month to run. Goal: 25–50 paying customers in 6–12 months, ~£5k MRR. Later expansion: driver messaging, multi-yard support, accounting integrations.
