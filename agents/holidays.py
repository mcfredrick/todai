"""Holiday detection for Tenkai posts.

Featured holidays are obscure/nerd ones that get extra emphasis.
Regular holidays get a light thematic nod.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import NamedTuple


class Holiday(NamedTuple):
    name: str
    emoji: str
    featured: bool  # True = obscure/nerd holiday, gets elaborate banner + heavier theming
    theme: str      # LLM theming guidance injected into the writing prompt


# (month, day) -> Holiday
_FIXED: dict[tuple[int, int], Holiday] = {
    (1, 1): Holiday(
        "New Year's Day", "🎆", False,
        "Ring in the new year! Frame today's AI/ML news as a fresh start — resolutions, "
        "predictions, and what the year ahead might hold for the field. What's the one release "
        "from today's digest you'd put in a time capsule? Use 🎆🥂✨ emojis throughout.",
    ),
    (1, 2): Holiday(
        "Science Fiction Day", "🚀", True,
        "It's Science Fiction Day — celebrating Isaac Asimov's birthday and the genre that "
        "predicted half of today's headlines. The line between sci-fi and the ML lab keeps "
        "shrinking. Frame today's news through the lens of classic sci-fi: which story does "
        "each item belong in? What would Asimov, Le Guin, or Dick make of this? "
        "Use 🚀🤖⭐🌌 emojis throughout.",
    ),
    (2, 2): Holiday(
        "Groundhog Day", "🦔", True,
        "Groundhog Day! In AI, every week feels like Groundhog Day — another 'best open-source "
        "model,' another benchmark claim, another RAG tutorial. Write today's post as if you've "
        "already lived this exact news cycle seventeen times. Weary but still showing up. "
        "Did the groundhog see its shadow? Six more months of LLM hype. Use 🦔🔮🔁 emojis.",
    ),
    (2, 14): Holiday(
        "Valentine's Day", "💝", False,
        "Valentine's Day! Write today's AI news with a little romantic flair. Which models have "
        "great chemistry together? What open-source projects would you swipe right on? Which "
        "paper made your heart skip a beat (or your GPU fan spin up)? Keep it fun and tasteful. "
        "Use 💝❤️🌹 emojis throughout.",
    ),
    (3, 14): Holiday(
        "Pi Day", "🥧", True,
        "Pi Day (3.14159265...) — the most sacred of nerd holidays. Full math mode. Weave π "
        "into everything: parameter counts approximating multiples of π, training runs measured "
        "in pie slices, the infinite non-repeating nature of a good training set. The synthesis "
        "section must reference π at least once. If a number is close to a multiple of π, point "
        "it out. Maximum nerd energy. Use 🥧🔢🧮 emojis throughout.",
    ),
    (3, 17): Holiday(
        "St. Patrick's Day", "🍀", False,
        "St. Patrick's Day! Luck is in the air — or at least, in the eval scores. Which projects "
        "got lucky with their benchmarks? What's the open-source pot of gold at the end of the "
        "rainbow? Which model release feels like finding a four-leaf clover? "
        "Use 🍀☘️🌈🍺 emojis throughout.",
    ),
    (4, 1): Holiday(
        "April Fools' Day", "🤡", False,
        "April Fools' Day! Write today's post with maximum healthy skepticism — every claim "
        "is potentially a prank until proven otherwise. Which benchmark results smell fishy? "
        "Which 'breakthrough' sounds like satire written by the product's own marketing team? "
        "Call it out. Lean into the absurdity of ML hype with a knowing wink. "
        "Use 🤡🃏🎭 emojis sparingly.",
    ),
    (4, 22): Holiday(
        "Earth Day", "🌍", False,
        "Earth Day! The compute bill is real and so is the planet. Ground every story in its "
        "energy and environmental angle where it applies — training costs, inference efficiency, "
        "data center footprints. Celebrate anything that's genuinely more efficient. "
        "Use 🌍🌱♻️☀️ emojis throughout.",
    ),
    (4, 23): Holiday(
        "World Book Day", "📚", True,
        "World Book Day! AI was trained on the world's books — all of them, controversially. "
        "Lean into the literary angle: what genre is today's model release? Which paper reads "
        "like a thriller? Which dataset is a tragedy? Frame the synthesis like a book review. "
        "Use 📚📖✍️ emojis throughout.",
    ),
    (5, 4): Holiday(
        "Star Wars Day", "⭐", True,
        "May the 4th be with you! Full Star Wars theming, all the way in. Which models are the "
        "Rebel Alliance? Which are the Empire? Is this week's open-source release the chosen "
        "one? Are transformers the midi-chlorians of AI? The synthesis section should contain "
        "at least one 'may the fourth be with you' equivalent pun. "
        "Use ⭐🚀⚔️🤖 emojis throughout.",
    ),
    (5, 25): Holiday(
        "Towel Day", "🏊", True,
        "Towel Day — the Hitchhiker's Guide to the Galaxy tribute! Don't panic. The Answer is "
        "42, which turns out to also be the number of times someone claimed AGI this quarter. "
        "Frame today's AI news through the lens of Douglas Adams: the Earth was a giant "
        "computer, the mice were running the experiment, and Marvin the Paranoid Android "
        "would have strong opinions about today's model releases. "
        "Use 🏊🌌🐋🌻 emojis throughout.",
    ),
    (6, 17): Holiday(
        "Eat Your Vegetables Day", "🥦", True,
        "It's Eat Your Vegetables Day — a holiday of absolutely no cultural significance "
        "whatsoever, which makes it perfect. Apply nutritional metaphors to AI with complete "
        "commitment: which models are all empty calories with zero nutritional value, which are "
        "actually good for you, which ones are the candy bar disguised as a health food? "
        "The synthesis should conclude with a balanced meal recommendation. "
        "Use 🥦🥗🍔🥕 emojis throughout.",
    ),
    (7, 4): Holiday(
        "Independence Day", "🎇", False,
        "Independence Day! Freedom and open source go hand in hand. Which tools are declaring "
        "independence from closed ecosystems today? What's the AI equivalent of 'no taxation "
        "without representation' — closed weights? API lock-in? Frame open-source releases as "
        "acts of liberation and proprietary systems as the loyalists. "
        "Use 🎇🦅🗽🔥 emojis throughout.",
    ),
    (7, 14): Holiday(
        "Bastille Day", "🇫🇷", True,
        "Bastille Day! The French Revolution, but for AI — which entrenched incumbents are "
        "being stormed by open-source upstarts today? Liberté, Égalité, Open Weights! "
        "The aristocracy of closed-source foundation models trembles. "
        "Write with revolutionary fervor. Liberté! Use 🇫🇷⚔️🏰 emojis throughout.",
    ),
    (7, 17): Holiday(
        "World Emoji Day", "🎉", True,
        "World Emoji Day 🎉! This is the one day where maximum emoji usage is not just "
        "permitted but required. Use emojis in EVERY sentence — multiple per bullet, in "
        "section headers, in the synthesis. The more the better. Every technical term gets "
        "an emoji companion. Go absolutely wild. The usual restraint is suspended. "
        "🚀🤖💥🔥⭐🧠📄🛠️✨💡🎯🏆",
    ),
    (7, 22): Holiday(
        "Pi Approximation Day", "🥧", True,
        "Pi Approximation Day — July 22nd, because 22÷7 ≈ π. The scrappier, less glamorous "
        "cousin of March 14th, and we love it anyway. Same π energy as Pi Day but with a "
        "more approximate, imprecise vibe that feels very on-brand for the current state of "
        "AI benchmarking. Round every number to the nearest approximation of π. "
        "Use 🥧🔢≈ emojis throughout.",
    ),
    (8, 13): Holiday(
        "International Left-Handers Day", "🤚", True,
        "International Left-Handers Day — for the 10% who do things differently. "
        "Frame today's news around contrarian takes, underdogs, and approaches that go against "
        "the right-handed grain of the ML mainstream. Which project is doing the 'wrong' thing "
        "that might actually be right? Which consensus is worth challenging? "
        "Use 🤚✋↩️ emojis throughout.",
    ),
    (8, 26): Holiday(
        "National Dog Day", "🐕", True,
        "National Dog Day! Good boys and good models — rate every AI release as a dog breed "
        "with complete confidence. Is it a reliable golden retriever or a chaotic labrador "
        "puppy that chews your evaluation set? A greyhound (fast, thin) or a St. Bernard "
        "(huge, occasionally useful)? The synthesis should produce a final 'best in show' "
        "recommendation. Use 🐕🐶🦴🏆 emojis throughout.",
    ),
    (9, 19): Holiday(
        "Talk Like a Pirate Day", "🏴‍☠️", True,
        "Arrr, it be International Talk Like a Pirate Day, ye scallywags! Write the entire "
        "post in full pirate speak — matey, arrr, avast, shiver me timbers. Every model be "
        "a ship, every benchmark be buried treasure, every hallucination be a Kraken draggin' "
        "yer prompt into the depths. The synthesis be yer treasure map to actionable loot. "
        "Use 🏴‍☠️⚓🦜💀 emojis throughout, arrr!",
    ),
    (10, 31): Holiday(
        "Halloween", "🎃", False,
        "Halloween! The AI news is haunted today. Ghost models that refuse to die, zombie "
        "papers from three years ago repackaged as breakthroughs, and the creeping specter "
        "of benchmark overfitting lurking in the shadows. Section headers should have a spooky "
        "edge. The synthesis should feel like a campfire horror story with a practical punchline. "
        "Use 🎃👻🦇🕸️🕯️ emojis throughout.",
    ),
    (11, 11): Holiday(
        "Veterans Day", "🎖️", False,
        "Veterans Day — a day to honor those who served. Keep the tone measured and respectful. "
        "Where AI intersects with veteran support, accessibility, or public service, highlight "
        "it genuinely. Technical precision is the order of the day.",
    ),
    (11, 30): Holiday(
        "Computer Security Day", "🔐", True,
        "Computer Security Day — the one day a year we officially acknowledge that everything "
        "is probably compromised. Frame every AI story through the security lens: what attack "
        "surface does this open, what's being hardened, what's a disaster waiting to happen? "
        "The synthesis should include at least one concrete threat model. "
        "Use 🔐🛡️💀🔓⚠️ emojis throughout.",
    ),
    (12, 9): Holiday(
        "Pretend to Be a Time Traveler Day", "⏰", True,
        "Pretend to Be a Time Traveler Day! Write today's entire post from the perspective "
        "of someone who's traveled back from 2035 to observe these quaint early AI systems. "
        "How adorable that we thought this was impressive! How charmingly primitive the "
        "tooling! The condescension should be affectionate, not mean — the time traveler "
        "genuinely loved this era, bumpy as it was. "
        "Use ⏰🕰️🌀🔭 emojis throughout.",
    ),
    (12, 21): Holiday(
        "Winter Solstice", "❄️", True,
        "Winter Solstice — the longest night of the year, when the darkness peaks and the "
        "light begins its slow return. A perfect metaphor for the AI hype cycle. Frame "
        "today's news as things that shine brightest in the dark: the small, steady lights "
        "vs the blinding flares that leave you night-blind. "
        "Use ❄️🌙⭐🕯️ emojis throughout.",
    ),
    (12, 25): Holiday(
        "Christmas", "🎄", False,
        "It's Christmas! What's under the open-source tree this year? Which model releases "
        "are actual gifts, and which are the socks no one asked for? Write with festive energy "
        "— the good kind, not the corporate-holiday-party kind. "
        "Use 🎄🎁⭐❄️🦌 emojis throughout.",
    ),
    (12, 26): Holiday(
        "Boxing Day", "📦", True,
        "Boxing Day — the holiday of boxes, packages, and repackaged leftovers. Which of "
        "today's 'new' releases is yesterday's news in a fresh container? Which Docker image "
        "deserves a bow? What's getting wrapped up for shipping? Find the packaging metaphor "
        "in everything. Use 📦🎁🐳📮 emojis throughout.",
    ),
    (12, 31): Holiday(
        "New Year's Eve", "🥂", False,
        "New Year's Eve — the year's final digest. Write it like a midnight toast: what are "
        "we leaving behind, what do we carry into the next year, and is the open-source "
        "ecosystem we're celebrating worth the champagne? Make the synthesis a proper farewell. "
        "Use 🥂🎆🎉✨ emojis throughout.",
    ),
}


def _first_weekday(year: int, month: int, weekday: int) -> date:
    """First occurrence of weekday (Mon=0...Sun=6) in the given month."""
    d = date(year, month, 1)
    return d + timedelta(days=(weekday - d.weekday()) % 7)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """Nth occurrence (1-indexed) of weekday in the given month."""
    return _first_weekday(year, month, weekday) + timedelta(weeks=n - 1)


def _last_weekday(year: int, month: int, weekday: int) -> date:
    """Last occurrence of weekday in the given month."""
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    return last_day - timedelta(days=(last_day.weekday() - weekday) % 7)


def get_holiday(post_date: date) -> Holiday | None:
    """Return the Holiday for the given date, or None."""
    fixed = _FIXED.get((post_date.month, post_date.day))
    if fixed:
        return fixed

    year = post_date.year

    # Thanksgiving — 4th Thursday of November (Thursday = 3)
    if post_date == _nth_weekday(year, 11, 3, 4):
        return Holiday(
            "Thanksgiving", "🦃", False,
            "Thanksgiving! Give thanks for open-source weights, free API tiers, papers that "
            "include reproducible code, and maintainers who answer issues on a holiday weekend. "
            "What's the ML dish you're most grateful for this year? "
            "Use 🦃🥧🍂🌽 emojis throughout.",
        )

    # International Programmers' Day — 256th day of the year (Sep 13 non-leap, Sep 12 leap)
    if post_date == date(year, 1, 1) + timedelta(days=255):
        return Holiday(
            "International Programmers' Day", "💻", True,
            "International Programmers' Day — the 256th day of the year, because of course "
            "it is. Full nerd ceremony. Celebrate the humans who actually wrote the code: the "
            "kernel devs, the framework maintainers, the person who filed the issue that fixed "
            "a bug you hit last week. Reference 256 wherever it fits (and force it where it "
            "doesn't). Use 💻🔢⌨️🐛 emojis throughout.",
        )

    # System Administrator Appreciation Day — last Friday of July (Friday = 4)
    if post_date.month == 7 and post_date == _last_weekday(year, 7, 4):
        return Holiday(
            "System Administrator Appreciation Day", "🖥️", True,
            "System Administrator Appreciation Day! The unsung heroes keeping GPU clusters "
            "warm, CUDA drivers current, and Kubernetes from imploding. Today's AI news would "
            "be impossible without them. Frame everything through the ops lens — not just what "
            "shipped, but what it costs to run it. Use 🖥️🔧⚙️🙏 emojis throughout.",
        )

    # Ada Lovelace Day — second Tuesday of October (Tuesday = 1)
    if post_date.month == 10 and post_date == _nth_weekday(year, 10, 1, 2):
        return Holiday(
            "Ada Lovelace Day", "🖊️", True,
            "Ada Lovelace Day — celebrating women in computing and STEM. The first programmer "
            "wrote her algorithms in 1843. Today, highlight women's contributions to AI/ML "
            "wherever they appear in the news, with genuine enthusiasm and zero tokenism. "
            "Use 🖊️💡⭐🔬 emojis throughout.",
        )

    return None
