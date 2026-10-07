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

If they don't know where their email is hosted, find out now (step 5 shows how).
It's the one thing that turns a launch into an emergency.

## 2. Build the site (the starter kit)

1. **Calls tab → Draft their site** writes `outreach/sites/<firm>/site.json`,
   already filled in from everything known: their sheet row, their old site,
   and their onboarding answers and uploads. What they told you counts as
   confirmed; anything only guessed is marked `[Confirm: ...]`.
2. Go through `site.json` with them (or from their answers): headline, a line
   per service, towns covered, guarantee, reviews, FAQs. Add the dashboard's
   `tenant_id` and `site_key` from `/admin`. Put photos in `client-files/` and
   list them (`hero_photo`, `gallery.photos`, a `photo` per service).
3. **Automation tab → Build site** (folder name). It builds `site/`: home,
   services, gallery, reviews, contact (photos too), a page per town, thanks,
   privacy, 404, sitemap, redirects and security headers, all wired to the
   dashboard. It **won't build** while anything still says `[Confirm` or the
   dashboard ids are missing - the log lists exactly what. Tick **Draft build**
   to preview it anyway (yellow banner, hidden from Google; Publish refuses it).
4. Check it on your phone (open `site/index.html`), then publish.

A star rating only appears if both `reviews.rating` and `reviews.count` are
filled in - real numbers from their Google profile, never estimated. Limited
companies must show their registered details on their website; the footer does
it from `company`.

## 3. Hosting: Cloudflare Pages, on the client's account

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

## 4. Forms and enquiries (every client)

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

## 5. Pointing the domain - without breaking their email

**On the panel:** Clients → *Go live without breaking their email* → type their
domain → **1. Save their DNS** does steps 1 and 5 for you: it saves every record
their email needs (`outreach/sites/<firm>/dns-before.json`) and says who hosts
their email. After the switch, **2. Check the launch** compares, and lists any
record that went missing with exactly what to add in Cloudflare.

1. **Before touching anything**, screenshot or export every DNS record at their
   registrar. The ones that matter most:
   - `MX` records - their email. Lose these and their email stops.
   - `TXT` records - SPF (`v=spf1 ...`), DKIM, DMARC, Google/Microsoft verification.
   - `CNAME` records like `autodiscover`, `mail`, `selector1._domainkey`.
2. Easiest route: in Cloudflare, *Add a site* with their domain on the Free plan.
   Cloudflare imports the existing records - **check every one from your
   screenshot is there** (especially MX and TXT) before going on.
3. Change the nameservers at their registrar to the two Cloudflare gives you. Usually the client has to
   do this: paste the two into the panel and press **Client's nameserver guide** - a one-page guide for
   their registrar to send them, and the Telegram bot texts you the moment the switch happens.
4. In the Pages project: *Custom domains → Set up a domain* for both
   `theirdomain.co.uk` and `www.theirdomain.co.uk`. SSL is automatic.
5. Send a test email **to** and **from** their address once it's live.

## 6. Keeping their Google ranking

- **Redirect old pages.** List the old site's URLs first (`site:theirdomain.co.uk`
  on Google, or their old sitemap). Any page that's moved gets a line in a
  `_redirects` file in the site root, e.g. `/our-services /services 301`.
- Google Search Console: add the domain (Cloudflare can add the DNS record for
  you), then submit `sitemap.xml`.
- Google Business Profile: check the website link points at the new site.

## 7. Launch checks (15 minutes)

**Check the launch** on the panel does every box below that a computer can tick
(https, www, http → https, a real 404, sitemap and robots, no draft or noindex,
tracking and the quote form wired up, certificate, email records) and says
READY or what's wrong. The phone, enquiry and email tests are still by hand.

- [ ] On your own phone: every page, tap-to-call works, WhatsApp opens, menu works
- [ ] Send a test enquiry through the form - it arrives in the dashboard and by email
- [ ] `https://` everywhere, no warnings; `www` and non-`www` both work
- [ ] A made-up URL shows a proper 404 page
- [ ] Their email still sends and receives (step 5.5)
- [ ] **Launch report** on the panel (their old website, new site if the domain
      changed) - 90+ speed score before you send it

## 8. After launch

- [ ] Send them the launch report
- [ ] `/admin` → their card → set **launched on** (starts their aftercare reminders)
- [ ] `/admin` → Launched customers → add their live site (hourly uptime check) and send the **£39/month card link** (nothing is charged until the free period ends)
- [ ] Ask for the Google review and, for founding clients, the 60-second video
- [ ] Give them their referral link (`/refer`)
- [ ] Add a line to your own case studies once they're happy to be named
