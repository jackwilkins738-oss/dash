import type { QA } from '@/components/faq'

export type Trade = {
  slug: string
  /** Short label used in nav, cards and breadcrumbs */
  label: string
  /** Who the page is for, used in titles */
  audience: string
  metaTitle: string
  metaDescription: string
  eyebrow: string
  h1: string
  lede: string
  intro: string
  mustHave: { title: string; body: string }[]
  faqs: QA[]
}

// Each page is written for that trade specifically. Nothing here claims results, clients or
// credentials the business doesn't have: it describes what a good site for the trade needs
// and what Scalar Digital builds.
export const TRADES: Trade[] = [
  {
    slug: 'roofers',
    label: 'Roofers',
    audience: 'roofing firms',
    metaTitle: 'Website Design for Roofers',
    metaDescription:
      'Fast, fixed-price websites for roofing firms: tap-to-call for emergencies, clear service areas and proof of your work. Hand-coded, from £750.',
    eyebrow: 'Websites for roofers',
    h1: 'A roofing website that wins the job, not just the visit.',
    lede: 'When a roof is leaking nobody scrolls patiently. They search on a phone, tap the first firm that looks trustworthy and ring.',
    intro:
      'A roofing customer decides fast and often under pressure, so your website has seconds to look safe, local and easy to reach. Most roofing sites lose that moment: they load slowly on a weak signal, hide the phone number, or describe every service on one long page nobody reads. A site built around how roofing customers actually behave fixes each of those.',
    mustHave: [
      {
        title: 'A call button that is always in reach',
        body: 'Emergency and repair enquiries are decided on a phone, often with one thumb. A tap-to-call and WhatsApp button that follows the visitor down the page turns a panicked search into a phone call.',
      },
      {
        title: 'A page for each job people search for',
        body: 'Pitched roofs, flat roofs, repairs, chimney work, fascias and gutters are different searches. One page per service can be found for what it covers, and each can answer the real questions a customer has about that job.',
      },
      {
        title: 'The areas you cover, stated plainly',
        body: 'Customers search with a town in mind. Listing the places you genuinely work, on a page with real detail about them, helps the right people in the right postcode find you and helps you rule out jobs too far away.',
      },
      {
        title: 'Proof rather than promises',
        body: 'Before and after photos of your own work, guarantees written down, and accreditations only if you genuinely hold them. A roof is a big spend, and specifics reassure more than adjectives.',
      },
      {
        title: 'Speed on a weak signal',
        body: 'People search from vans, driveways and gardens, often on mobile data. A lightweight, hand-coded page loads while a heavy WordPress theme is still thinking, and Google measures that speed too.',
      },
      {
        title: 'A quote form that takes thirty seconds',
        body: 'Name, number, postcode and a line about the job. The fewer fields, the more enquiries. The information lands with you straight away so you can reply before the next firm does.',
      },
    ],
    faqs: [
      {
        q: 'What should a roofing company website include?',
        a: 'A prominent phone number and WhatsApp button, a separate page for each type of job you do, the areas you cover, photos of your own completed work, any guarantees or accreditations you genuinely hold, and a short quote form. It should also load quickly on a phone, because most roofing searches happen on one.',
      },
      {
        q: 'Do I need a separate page for every town I cover?',
        a: 'Only where you genuinely work and have something real to say. One useful page per area, with actual local detail, works better than many near-identical pages with the town name swapped. Search engines and customers can both tell the difference.',
      },
      {
        q: 'Can I get a roofing website for a fixed price?',
        a: 'Yes. Scalar Digital builds a single hand-coded landing page from £750, or a full five-page site with a private dashboard for enquiries, quotes and invoices for £2,500. The price is agreed before any work starts and does not change.',
      },
    ],
  },
  {
    slug: 'loft-conversion-companies',
    label: 'Loft conversion firms',
    audience: 'loft conversion companies',
    metaTitle: 'Website Design for Loft Conversion Firms',
    metaDescription:
      'Fixed-price websites for loft conversion firms: explain the process, show real conversions and answer the planning and cost questions customers ask. From £750.',
    eyebrow: 'Websites for loft conversion firms',
    h1: 'A website that makes a loft conversion feel like a safe decision.',
    lede: 'Homeowners spend weeks researching before they ring anyone. Your site is where that research either ends with you or moves on.',
    intro:
      'A loft conversion is one of the biggest jobs a household commissions, and customers know it. They compare conversion types, worry about planning and disruption, and read what you say slowly. A loft conversion website that answers those worries in plain language, backed by real projects, shortlists you before you have spoken to anyone.',
    mustHave: [
      {
        title: 'The process, explained step by step',
        body: 'Design, planning or permitted development, building regulations, the build itself, sign-off. Customers fear the unknown more than the cost. Showing the steps and roughly how long each takes removes a lot of that fear.',
      },
      {
        title: 'A page for each conversion type',
        body: 'Velux, dormer, hip-to-gable and mansard conversions suit different houses and are searched for separately. A page for each lets a homeowner see themselves in your work and lets you be found for the type that fits.',
      },
      {
        title: 'Honest guidance on cost',
        body: 'Customers filter themselves by budget. Explaining what affects the price, and giving a sensible guide range if you are comfortable with one, saves you calls from people who were never going to proceed and builds trust with the ones who will.',
      },
      {
        title: 'Real projects, with detail',
        body: 'Photos of completed conversions with a few lines on the house, the type and what the homeowner wanted. Detail is what separates a firm that does this every week from one that has done it once.',
      },
      {
        title: 'Planning and regulations answered',
        body: 'Whether a conversion falls under permitted development, party wall matters and building control are the questions homeowners search. Answering them on your own site keeps the visitor with you and shows you know the process.',
      },
      {
        title: 'An enquiry form that asks the right things',
        body: 'Property type, roughly what they have in mind and their postcode. It qualifies the lead before you call and makes the visitor feel taken seriously.',
      },
    ],
    faqs: [
      {
        q: 'What makes a good loft conversion website?',
        a: 'Clear pages for each conversion type, photos and short write-ups of real projects, an honest explanation of the process, planning and building regulation answers, and a simple enquiry form. It also needs to load fast on a phone, since many homeowners first research on one.',
      },
      {
        q: 'Should a loft conversion company show prices online?',
        a: 'You do not have to give exact prices, but explaining what drives the cost, and offering a realistic guide range if you can, helps. It filters out poor-fit enquiries and shows customers you are straightforward.',
      },
      {
        q: 'Is it worth having a page for each type of conversion?',
        a: 'Yes, if each page says something useful about that type. Homeowners often search for a specific type such as a dormer or hip-to-gable, and a dedicated page can answer that question and be found for it.',
      },
    ],
  },
  {
    slug: 'driveway-installers',
    label: 'Driveway installers',
    audience: 'driveway and paving installers',
    metaTitle: 'Website Design for Driveway Installers',
    metaDescription:
      'Fast, fixed-price websites for driveway and paving installers: a page for every surface, before-and-after galleries and quote forms that convert. From £750.',
    eyebrow: 'Websites for driveway installers',
    h1: 'A website that turns driveway searches into booked surveys.',
    lede: 'Customers compare resin, block paving, tarmac and more, then judge you on photos. Your site should make that comparison easy and win it.',
    intro:
      'Driveways are a visual, comparison-driven purchase. Homeowners look at surfaces, look at finished work and look at reviews before they get a quote. Most installers show a handful of small photos and a phone number. A site built for this trade puts every surface on its own page, leads with your best finished work and makes it quick to ask for a survey.',
    mustHave: [
      {
        title: 'A page for each surface you install',
        body: 'Resin bound, block paving, tarmac, imprinted concrete and gravel are separate searches with different questions. Each page can explain the surface honestly, who it suits and how it wears, which is what customers are trying to decide.',
      },
      {
        title: 'A gallery that sells the finish',
        body: 'Before and after photos are the strongest thing a driveway installer owns. A gallery that loads quickly, with images properly sized so it does not slow the page, lets the work do the persuading.',
      },
      {
        title: 'Straight answers on the rules',
        body: 'Rules on paving over front gardens, permeable surfaces and drop kerbs confuse customers. A clear explanation of what usually applies, and when to check with the council, positions you as the firm that knows its job.',
      },
      {
        title: 'Areas and survey booking',
        body: 'State where you work and make it easy to book a free survey. The path from photo gallery to survey request should take a couple of taps on a phone.',
      },
      {
        title: 'Guarantees and materials in plain words',
        body: 'What is guaranteed, for how long, and what materials you use. Vague claims read as sales talk. Specifics read as confidence.',
      },
      {
        title: 'Reviews you can point to',
        body: 'Real customer comments, with permission, sit beside the work they refer to. Nothing invented, nothing you cannot back up.',
      },
    ],
    faqs: [
      {
        q: 'How do I make my driveway installation website stand out?',
        a: 'Lead with your best finished work, give each surface its own page with honest information, and make booking a survey easy on a phone. Specific detail about your materials and guarantees does more than general claims.',
      },
      {
        q: 'Will a photo gallery slow my website down?',
        a: 'Not if the site is built properly. Images can be sized for the screen and loaded as the visitor scrolls, so a full gallery still opens quickly on a phone. Slow galleries are usually a sign of a heavy theme or unoptimised photos.',
      },
      {
        q: 'Should I list prices per square metre?',
        a: 'It is up to you. Explaining what affects the cost of each surface usually helps, and a guide range can help filter enquiries. Whatever you show should be accurate, because customers will hold you to it.',
      },
    ],
  },
  {
    slug: 'landscapers',
    label: 'Landscapers',
    audience: 'landscapers and garden designers',
    metaTitle: 'Website Design for Landscapers',
    metaDescription:
      'Fixed-price websites for landscapers and garden designers: a portfolio that sells the finish, clear services and simple enquiries. Hand-coded, from £750.',
    eyebrow: 'Websites for landscapers',
    h1: 'A website as well kept as the gardens you build.',
    lede: 'Landscaping is sold with photographs. If your site does not do your gardens justice, nobody sees why they should pay for them.',
    intro:
      'People buy a garden with their eyes first. Your website is the portfolio a customer flicks through on a phone before deciding whether to ring, so it has to show your best work large, sharp and quickly. It also has to make clear what you actually offer: design, build, maintenance, or some mix, and where you work.',
    mustHave: [
      {
        title: 'A portfolio built around your best projects',
        body: 'A few complete projects with several photos and a short story each beat a wall of unrelated pictures. Show the design idea, the finished result and the type of space.',
      },
      {
        title: 'Clear separation of what you offer',
        body: 'Design and build, hard landscaping, planting and ongoing maintenance attract different customers. Separate pages let each visitor find their own service without wading through the rest.',
      },
      {
        title: 'Seasonal relevance',
        body: 'Garden work comes in seasons. A site that reflects what people are planning now, such as autumn planting or spring patios, feels current and gives a returning visitor a reason to look.',
      },
      {
        title: 'A simple way to start a conversation',
        body: 'A short form or a WhatsApp message with a couple of photos of the space is often all a customer wants for a first chat. Make that step easy.',
      },
      {
        title: 'Speed with a lot of imagery',
        body: 'Landscaping sites are image-heavy, which is exactly where slow sites suffer. Hand-coded pages with properly sized images stay quick on mobile even with a big portfolio.',
      },
      {
        title: 'Areas you cover and who you are',
        body: 'A garden is a personal job. Customers want to know where you work and who will turn up. A short, genuine introduction helps them feel comfortable inviting you in.',
      },
    ],
    faqs: [
      {
        q: 'How many photos should a landscaping website have?',
        a: 'Quality and completeness matter more than volume. A handful of finished projects, each with several good photos and a few lines of context, is more persuasive than dozens of unrelated images. Make sure they load quickly on a phone.',
      },
      {
        q: 'Should garden design and maintenance be on the same site?',
        a: 'Yes, as long as they are clearly separated. Give each its own page so a customer looking for maintenance is not confused by design-and-build content, and vice versa.',
      },
      {
        q: 'Is a blog worth it for a landscaper?',
        a: 'It can be, if you write genuinely useful posts, such as what to plant in a shady garden or how long a patio takes. Regular, helpful posts can bring in searches. Thin or copied posts do not, so only start one if you can keep it useful.',
      },
    ],
  },
  {
    slug: 'builders-and-extension-firms',
    label: 'Builders & extensions',
    audience: 'builders and house extension firms',
    metaTitle: 'Website Design for Builders and Extensions',
    metaDescription:
      'Fast, fixed-price websites for builders and extension firms: real project case studies, clear process and enquiries that arrive with the detail you need. From £750.',
    eyebrow: 'Websites for builders and extension firms',
    h1: 'A website that gets you shortlisted for the extension, not just the quick fix.',
    lede: 'Extension customers want a firm they can trust with their home for months. Your site is their first look at how you work.',
    intro:
      'An extension or major renovation means weeks of strangers in the house and a large sum of money. Homeowners are cautious, so they compare several firms and read closely. A website for builders should show finished projects with real detail, explain how you run a job, and make it simple to start a conversation. Most builders say little of this online.',
    mustHave: [
      {
        title: 'Project case studies with substance',
        body: 'For each project, the type of property, what was built, roughly how long it took and what the homeowner wanted. Detail is the proof that you finish what you start.',
      },
      {
        title: 'How you run a job',
        body: 'Who they will deal with, how you communicate, how changes are agreed and how the site is left each day. Homeowners worry about these more than they say. Answering them wins trust early.',
      },
      {
        title: 'Planning and building regulations',
        body: 'Explaining how you handle drawings, planning permission or permitted development, and building control shows you manage the whole process, not just the building.',
      },
      {
        title: 'Clear handling of cost and changes',
        body: 'Fixed quotes, and a written agreement for anything that changes the scope. It is the difference between a smooth job and a dispute, and saying so up front sets you apart.',
      },
      {
        title: 'The people behind the business',
        body: 'A short, genuine introduction to who you are, with a real photo if you are comfortable, helps a homeowner picture you in their house. Include accreditations only if you genuinely hold them.',
      },
      {
        title: 'Enquiries that arrive ready to answer',
        body: 'A form that asks for the property, the idea and the postcode means your first call is informed. The enquiry goes straight to you, so you can reply quickly.',
      },
    ],
    faqs: [
      {
        q: 'What should a builder’s website include?',
        a: 'Detailed case studies of finished projects, an explanation of how you run a job and handle changes, information on planning and building regulations, the areas you cover, and a simple enquiry form. It should also be fast on a phone, because homeowners often start their search on one.',
      },
      {
        q: 'How can a builder’s website build trust?',
        a: 'By being specific: real projects, real photos, honest explanations of process and cost, and only claims you can back up. Vague promises read as marketing. Detail reads as experience.',
      },
      {
        q: 'Does a builder need a dashboard as well as a website?',
        a: 'Not necessarily, but it helps once enquiries and quotes grow. The full Scalar Digital build includes a private dashboard for enquiries, quotes, jobs and invoices, hosted free for the first 12 months, so the site brings the lead in and the dashboard helps run the job.',
      },
    ],
  },
]

export const TRADE_BY_SLUG = Object.fromEntries(TRADES.map((t) => [t.slug, t])) as Record<string, Trade>
