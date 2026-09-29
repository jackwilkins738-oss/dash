# Launching a client's site

The same steps for every build, so a launch never breaks a client's email,
loses their Google ranking, or leaves their enquiries going nowhere. About an
hour, most of it waiting for DNS.

**The promise this keeps:** "no monthly fees on your website, and you own it
outright". So the site is hosted free, on the client's own account, and they
could walk away with everything.

---

## 1. Before you start building

From their onboarding page (dashboard → `/onboarding`) you should already have:

- [ ] Who their domain is registered with, and **the login** (or they'll log in with you on a call)
- [ ] Where their email is hosted (Google Workspace, Microsoft 365, their registrar...)
- [ ] Logo, photos, services, areas, guarantee, insurance, reviews link

If they don't know where their email is hosted, find out now (step 4 shows how).
It's the one thing that turns a launch into an emergency.

## 2. Hosting: Cloudflare Pages, on the client's account

Free, fast everywhere, commercial use allowed. (Vercel's free plan forbids
commercial use, so client sites don't go there.)

1. Create a Cloudflare account **in the client's name, with their email** (sign
   up together on a call, or they do it and invite you: *Manage account →
   Members → Invite*, role *Administrator*).
2. *Workers & Pages → Create → Pages → Upload assets* (or connect a GitHub repo
   if you keep one per client). Upload the site folder.
3. You get a `*.pages.dev` address - check the whole site there before any DNS change.

**Or from the panel:** put the finished site in `outreach/sites/<firm>/site/` and use
**Publish site** (needs `CLOUDFLARE_API_TOKEN` in Settings and Node.js installed). Give
their account id the first time; later publishes need only the folder name. Only the
`site` folder goes live - never their brief or uploaded photos.

## 3. Forms and enquiries (every client)

Every client gets a business on your dashboard, even on the £750 landing page -
it's what catches their enquiries.

1. `/admin` → **Add a new customer** (business name and slug), then on their
   card set **Enquiry alerts** to their email. Every enquiry is emailed there in
   full the moment it arrives - name, tap-to-call number, message - so they can
   ring back from the van without logging in.
2. Copy the `<script>` snippet it gives you into every page, just before `</body>`.
3. On the enquiry form: `<form data-lead-form>` with fields named `name`,
   `email`, `phone`, `message`. Page views are recorded automatically.
   Add `<input type="file" name="photos" multiple accept="image/*">` so customers
   can send up to 5 photos of the job - often enough to price it without a visit.
   (Optional: `data-lead-redirect="/thanks"` on the form to show a thank-you page.)
4. **Scalar build:** invite them (`/admin` → their card → invite) so they get the
   full dashboard - quotes, invoices, jobs, portal.
   **Landing page:** no login needed - they just get the enquiry emails. The
   dashboard isn't offered on the landing page; it comes only with the full build
   (free for 12 months, then £39 a month, optional).

## 4. Pointing the domain - without breaking their email

1. **Before touching anything**, screenshot or export every DNS record at their
   registrar. The ones that matter most:
   - `MX` records - their email. Lose these and their email stops.
   - `TXT` records - SPF (`v=spf1 ...`), DKIM, DMARC, Google/Microsoft verification.
   - `CNAME` records like `autodiscover`, `mail`, `selector1._domainkey`.
2. Easiest route: in Cloudflare, *Add a site* with their domain on the Free plan.
   Cloudflare imports the existing records - **check every one from your
   screenshot is there** (especially MX and TXT) before going on.
3. Change the nameservers at their registrar to the two Cloudflare gives you.
4. In the Pages project: *Custom domains → Set up a domain* for both
   `theirdomain.co.uk` and `www.theirdomain.co.uk`. SSL is automatic.
5. Send a test email **to** and **from** their address once it's live.

## 5. Keeping their Google ranking

- **Redirect old pages.** List the old site's URLs first (`site:theirdomain.co.uk`
  on Google, or their old sitemap). Any page that's moved gets a line in a
  `_redirects` file in the site root, e.g. `/our-services /services 301`.
- Google Search Console: add the domain (Cloudflare can add the DNS record for
  you), then submit `sitemap.xml`.
- Google Business Profile: check the website link points at the new site.

## 6. Launch checks (15 minutes)

- [ ] On your own phone: every page, tap-to-call works, WhatsApp opens, menu works
- [ ] Send a test enquiry through the form - it arrives in the dashboard and by email
- [ ] `https://` everywhere, no warnings; `www` and non-`www` both work
- [ ] A made-up URL shows a proper 404 page
- [ ] Their email still sends and receives (step 4.5)
- [ ] **Launch report** on the panel (their old website, new site if the domain
      changed) - 90+ speed score before you send it

## 7. After launch

- [ ] Send them the launch report
- [ ] `/admin` → their card → set **launched on** (starts their aftercare reminders)
- [ ] `/admin` → Launched customers → add their live site (hourly uptime check) and send the **£39/month card link** (nothing is charged until the free period ends)
- [ ] Ask for the Google review and, for founding clients, the 60-second video
- [ ] Give them their referral link (`/refer`)
- [ ] Add a line to your own case studies once they're happy to be named
