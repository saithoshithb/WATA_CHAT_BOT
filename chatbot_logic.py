"""Brain of the Hydrolytics chatbot. No Streamlit in here, so it can be tested on its own.

How it answers (in order):
  1. A ticket number like SAN-0001  -> looks the complaint up in the database.
  2. "supplied 1000 billed 800"     -> runs the water-balance leakage calculation.
  3. Anything else                  -> finds the best match in KNOWLEDGE (keyword + fuzzy match).
  4. No good match                  -> says so honestly and suggests topics.
"""
import difflib
import re

# ---------------------------------------------------------------------------
# Knowledge base. Each entry: (example questions / keywords, answer).
# Facts about microplastics come from the papers we read; edit freely.
# ---------------------------------------------------------------------------
KNOWLEDGE = [
    (["what is hydrolytics", "about the project", "what does your project do", "what is this app"],
     "**Hydrolytics** detects and counts microplastics in water. A water sample is filtered, stained "
     "with a dye that makes plastic glow, photographed with a cheap microscope, and software counts and "
     "sorts the particles. The same app also has a sanitation-complaint system, a water usage tracker "
     "and a leakage check."),
    (["what are microplastics", "define microplastic", "microplastic meaning", "what is microplastic"],
     "**Microplastics** are tiny plastic pieces, usually smaller than 5 mm. Some are made small on purpose "
     "(primary, like microbeads) and some come from bigger plastic breaking down (secondary)."),
    (["why are microplastics a problem", "are microplastics harmful", "health effects", "why do microplastics matter"],
     "They are found almost everywhere, including drinking water. Research says particle *shape* (fiber, "
     "fragment, sphere, foam, film) can change how harmful they are. Scientists are still studying the exact "
     "health effects, so we avoid making medical claims."),
    (["how common are microplastics in tap water", "tap water statistics", "how much plastic in water", "81%"],
     "A review by Pico and Barcelo (2019) reports human-made particles in about **81% of 159 tap-water "
     "samples**, nearly all of them fibers. About 1.5 million tonnes of primary microplastics enter water each year."),
    (["how does the detection work", "how does it count", "how does hydrolytics work", "method", "steps", "how do you detect microplastics", "how do you count particles", "how does it detect microplastics", "process", "how is water tested"],
     "Six steps: **sample** the water, **filter** it onto a membrane, **stain** with Nile Red dye so plastic "
     "glows, **image** it under blue light with a phone microscope, **analyse** the image in software, then "
     "**report** counts, sizes and shapes (CSV download)."),
    (["what is nile red", "nile red dye", "staining", "why does plastic glow"],
     "**Nile Red** is a dye that sticks to plastic and glows (fluoresces) under blue light, so plastic particles "
     "stand out from sand, dust and other material. Maes et al. (2017) recovered 96.6% of known plastic particles with it."),
    (["how accurate is it", "accuracy", "is it validated", "how reliable"],
     "Be honest: the high numbers are from **published studies** of the methods we build on (96.6% recovery with "
     "Nile Red; 98% of labelled particles found by an AI model on phone-microscope images). **Validating our own "
     "counts against lab data is our next milestone.**"),
    (["how much does it cost", "price", "cost", "cheap", "low cost", "budget"],
     "The imaging side is low cost: a 2025 study used a microscope clip costing about **$10** with a phone. We "
     "have not priced a full product yet."),
    (["what are the shape classes", "types of microplastics", "fiber fragment sphere foam film", "categories"],
     "Recent research sorts microplastics into five shapes: **fiber, fragment, sphere, foam and film**, plus "
     "background (everything that isn't plastic)."),
    (["what is segmentation", "image segmentation", "what is deep learning", "ai model"],
     "**Segmentation** means labelling every pixel in an image (for example 'fiber' or 'background'). "
     "**Deep learning** is AI that learns this from many example images. A 2025 paper does this for microplastics "
     "with a light, fast model suited to ordinary labs."),
    (["what is ftir", "raman", "lab methods", "how do labs identify plastic"],
     "**FTIR and Raman** are lab instruments that identify the exact plastic type. They are accurate but costly "
     "and slow, which is why a cheap screening step like ours helps."),
    (["is my water safe to drink", "is tap water safe", "is our water safe", "is drinking water safe"],
     "We can't tell you whether your water is safe: Hydrolytics counts microplastic particles in a sample, "
     "and the health effects are still being researched. For drinking-water safety, use certified lab tests "
     "or your local water authority."),
    (["which sdgs", "sustainable development goals", "sdg", "goals"],
     "We support **SDG 6** (clean water and sanitation), **SDG 14** (life below water), **SDG 12** (responsible "
     "consumption and production) and **SDG 9** (industry, innovation and infrastructure)."),
    (["who is it for", "target users", "who benefits", "audience"],
     "Water utilities, university labs, communities and NGOs, and makers of everyday products."),
    (["how do i file a complaint", "sanitation complaint", "report a problem", "report sewage", "complaint"],
     "Open **Sanitation Complaints**, fill in issue type, severity, location and description (photo optional), and "
     "submit. You get a ticket number like **SAN-0001**. Type that number here, or in the Track tab, to see its status."),
    (["how do i track my complaint", "complaint status", "ticket status"],
     "Type your ticket number (for example **SAN-0001**) in this chat, or use the *Track a complaint* tab."),
    (["staff dashboard", "admin password", "how do staff update complaints"],
     "Staff open the *Staff dashboard* tab and enter the staff password (set as an `ADMIN_PASSWORD` secret). "
     "They can filter complaints, change status and leave a note for the citizen."),
    (["water usage tracker", "track my water use", "how to log water", "daily target"],
     "On **Water Usage Tracker**, pick an activity (shower, laundry...), set how many times, and add it. You get "
     "daily and 7-day averages and a chart. The default target is 135 L per person per day (an Indian urban norm; "
     "confirm for your city) and you can change it in the sidebar."),
    (["what is the leakage check", "how does leakage work", "water balance", "non revenue water", "loss percentage"],
     "**Loss % = (supplied - billed) / supplied x 100.** If 1000 kL is supplied and 800 kL billed, 200 kL (20%) is "
     "unaccounted for. That *suggests* leakage but can also be meter errors or unbilled use. Warning at 20%, "
     "critical at 30% (adjustable placeholders). Try it: type `supplied 1000 billed 800`."),
    (["night flow test", "how to check for a leak at home", "hidden leak"],
     "Close every tap and stop appliances, note your meter, wait 1 to 2 hours (overnight is best), then note it "
     "again. If the reading moved, there may be a hidden leak."),
    (["technology", "tech stack", "built with", "what language", "which libraries"],
     "Python and **Streamlit** for the web app, **pandas** for data tables, **SQLite** for storage, and image "
     "processing for the microplastic counter."),
    (["future plans", "next steps", "roadmap", "what next"],
     "**Validate** our counts against lab data, **pilot** with a utility or college lab, then **scale** with a "
     "hardware kit and a hosted data platform."),
    (["data privacy", "is my data safe", "where is data stored"],
     "Complaints, usage logs and bills are stored in a small SQLite file on the server. On free Streamlit Cloud it "
     "can reset when the app restarts, so a real deployment needs a permanent database. Don't enter sensitive personal data."),
    (["contact", "team", "who made this"],
     "We are a student team (VIT Vellore) building Hydrolytics for a clean-water sustainability project. "
     "Add your team contact details here in chatbot_logic.py."),
]

SUGGESTIONS = [
    "What are microplastics?", "How does Hydrolytics detect them?", "How accurate is it?",
    "How do I file a complaint?", "How does the leakage check work?", "Which SDGs do you support?",
]

GREETING = ("Hey, I'm Wata! I'm the Hydrolytics assistant. Ask me about microplastics, how our detection works, "
            "or the complaint, usage and leakage tools. You can also type a ticket number like `SAN-0001`, "
            "or `supplied 1000 billed 800` for a quick leak check.")

_STOP = set("a an the is are of to in on for and or do does i it my you your how what why can me we our with this that".split())
_TICKET = re.compile(r"\bSAN[-\s]?(\d+)\b", re.I)
_NUM = r"(\d+(?:[.,]\d+)?)"
_SUP = re.compile(r"suppl\w*\D{0,15}" + _NUM, re.I)
_BIL = re.compile(r"bill\w*\D{0,15}" + _NUM, re.I)


_SYN = {"detect": "count", "identify": "count", "measure": "count", "test": "count", "tested": "count",
        "price": "cost", "expensive": "cost", "cheap": "cost", "leak": "leakage", "leaking": "leakage",
        "tool": "tech", "tools": "tech", "technology": "tech", "stack": "tech", "library": "tech",
        "libraries": "tech", "language": "tech", "track": "tracker", "log": "tracker", "logging": "tracker",
        "report": "complaint", "dirty": "complaint", "sewage": "complaint", "staff": "admin",
        "dashboard": "admin", "secure": "privacy", "security": "privacy"}


def _stem(w):
    for suf in ("ing", "es", "s", "ed"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            w = w[: -len(suf)]
            break
    return _SYN.get(w, w)


def _tokens(text):
    return {_stem(w) for w in re.findall(r"[a-z0-9%]+", text.lower()) if w not in _STOP}


# Words that appear in many entries carry little meaning, so weight each word by how rare it is.
_DF = {}
for _keys, _ans in KNOWLEDGE:
    for _w in set().union(*[_tokens(k) for k in _keys]):
        _DF[_w] = _DF.get(_w, 0) + 1


def _w(word):
    return 1.0 / _DF.get(word, 1) ** 0.7 if word in _DF else 0.0


def _num(s):
    return float(s.replace(",", ""))


class _Bal:
    def __init__(self, level, loss=0.0, loss_pct=0.0, message=""):
        self.level, self.loss, self.loss_pct, self.message = level, loss, loss_pct, message


def _simple_balance(sup, bil, warn, crit):
    """Same maths as leakage.water_balance, for when that file is not available."""
    if sup <= 0:
        return _Bal("invalid", message="Supplied volume must be greater than zero.")
    if bil < 0:
        return _Bal("invalid", message="Billed volume cannot be negative.")
    if bil > sup:
        return _Bal("invalid", message="Billed is more than supplied, so check the readings or units.")
    loss = sup - bil
    pct = loss / sup * 100
    level = "critical" if pct >= crit else "warning" if pct >= warn else "ok"
    msg = {"critical": "Critical loss level.", "warning": "Warning: loss is above the warning level.",
           "ok": "Loss is within the normal range."}[level]
    return _Bal(level, loss, pct, msg)


def answer_leakage(text, warn=20.0, crit=30.0):
    """Return a reply if the text has both a supplied and a billed number, else None."""
    ms, mb = _SUP.search(text), _BIL.search(text)
    if not (ms and mb):
        return None
    sup, bil = _num(ms.group(1)), _num(mb.group(1))
    try:
        import leakage as lk
        bal = lk.water_balance(sup, bil, warn, crit)
    except ImportError:  # standalone hosting: leakage.py is not in the repo
        bal = _simple_balance(sup, bil, warn, crit)
    if bal.level == "invalid":
        return f"I couldn't compute that: {bal.message}"
    return (f"Supplied **{sup:,.1f} kL**, billed **{bil:,.1f} kL**: unaccounted water is **{bal.loss:,.1f} kL "
            f"({bal.loss_pct:.1f}%)**.\n\n{bal.message}\n\n*This suggests possible leakage, but meter errors or "
            f"unbilled use can also cause a gap.*")


def answer_ticket(text, read=None, parse=None, ticket=None):
    """Look up a complaint. `read`/`parse`/`ticket` are db helpers (injected so tests need no database)."""
    m = _TICKET.search(text)
    if not m:
        return None
    if read is None:
        try:
            import db
            db.init()
            read, parse, ticket = db.read, db.parse_ticket, db.ticket
        except ImportError:  # standalone hosting: no complaints database here
            return ("Ticket lookup needs the full Clean Water app (the complaints database). "
                    "Open the Sanitation Complaints page there to track it.")
    cid = parse(f"SAN-{int(m.group(1)):04d}")
    row = read("SELECT * FROM complaints WHERE id = ?", (cid,)) if cid else None
    if row is None or row.empty:
        return "I couldn't find a complaint with that ticket number. Please check it and try again."
    r = row.iloc[0]
    out = (f"**{ticket(r.id)}: {r.status}**\n\n{r.category} at {r.location} (severity {r.severity}, "
           f"filed {r.created_at}).")
    if r.admin_note:
        out += f"\n\nStaff note: {r.admin_note}"
    return out


def best_match(text, min_score=0.3):
    """Pick the knowledge entry that best matches the question, or None."""
    q = text.lower().strip()
    qt = _tokens(q)
    known = [w for w in qt if w in _DF]
    if not known:
        return None, 0.0
    qweight = sum(_w(w) for w in known)
    best, best_score = None, 0.0
    for keys, ans in KNOWLEDGE:
        score = 0.0
        for k in keys:
            kt = _tokens(k)
            shared = qt & kt
            cover_q = sum(_w(w) for w in shared) / qweight          # how much of the question is explained
            cover_k = sum(_w(w) for w in shared) / max(sum(_w(w) for w in kt), 1e-9)
            fuzzy = difflib.SequenceMatcher(None, q, k).ratio()
            contains = 1.0 if (k in q and len(k) > 3) else 0.0
            score = max(score, 0.45 * cover_q + 0.25 * cover_k + 0.15 * fuzzy + 0.4 * contains)
        if score > best_score:
            best, best_score = ans, score
    return (best, best_score) if best_score >= min_score else (None, best_score)


def reply(text, warn=20.0, crit=30.0, read=None, parse=None, ticket=None):
    """Main entry point: returns the chatbot's answer to one user message."""
    text = (text or "").strip()
    if not text:
        return "Please type a question."
    # Anyone calling "wata" gets an answer: strip the name, then treat what is left as the message.
    text = re.sub(r"\bwata\b", " ", text, flags=re.I)
    text = re.sub(r"^[\s,.:;!?-]+|[\s,.:;-]+$", "", text)
    if not text:
        return "Hey, I'm Wata! I'm here. What would you like to know?\n\n" + GREETING
    if re.fullmatch(r"(hi|hello|hey|hii|yo|namaste)( there)?[!. ]*", text, re.I):
        return GREETING
    t = answer_ticket(text, read, parse, ticket)
    if t:
        return t
    leak = answer_leakage(text, warn, crit)
    if leak:
        return leak
    ans, _ = best_match(text)
    if ans:
        return ans
    return ("I'm not sure about that one. I can help with: " + "; ".join(SUGGESTIONS)
            + ". Try rephrasing, or ask your team.")
