"""What trade owners say on the phone, and an honest answer to each - for the panel's Calls tab and
Telegram (type "objections"). Every answer sticks to what the site already promises; none invents a figure.
"""

OBJECTIONS = [
    ("I get all my work from word of mouth.",
     "That's the best kind. Most people who hear about you still look you up before they ring - the site is what "
     "they find. It should back up what they've heard, not put them off."),
    ("I'm on Checkatrade / MyBuilder.",
     "Keep it. Those leads go to several firms at once and you pay for them; your own site is the one place a "
     "customer only sees you. Plenty of firms use both."),
    ("It's too expensive.",
     "It's one fixed price, agreed before anything starts, and you own the site outright - no monthly fee on it. "
     "Think what one job is worth to you: that's the bar it has to clear."),
    ("My mate / nephew built it.",
     "Fair enough - I'm not knocking it. The page I made just shows what Google measures on a phone. If the numbers "
     "were fine, you wouldn't need me."),
    ("Just send me some info.",
     "Happy to - the page I made is the info, and the link's in my email. Can I ask one thing first: where does "
     "most of your work come from at the moment?"),
    ("Not now - too busy.",
     "Busy is good. When's quieter? I'll ring you back then. (Log it as Call back with the date.)"),
    ("I've been burned by web people before.",
     "That's common. Fixed price before any work starts, you check the whole site on your phone before it goes "
     "live, and the code and domain are yours outright - you're never tied to me."),
]


def text() -> str:
    return "\n\n".join(f"\"{q}\"\n→ {a}" for q, a in OBJECTIONS)
