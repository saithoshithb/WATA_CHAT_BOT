import pandas as pd
import chatbot_logic as b

def check(q, must):
    r = b.reply(q)
    assert must.lower() in r.lower(), (q, r[:120])

check("hello", "Wata")
check("what are microplastics?", "tiny plastic")
check("how does Hydrolytics detect microplastics", "six steps")
check("what is nile red", "nile red")
check("how accurate is this?", "next milestone")
check("which SDGs", "SDG 6")
check("how do I file a complaint", "SAN-0001")
check("explain the leakage check", "Loss %")
check("supplied 1000 billed 800", "20.0%")
check("Supplied: 1,000 kL, billed: 650 kL", "35.0%")
check("supplied 0 billed 5", "couldn't compute")
check("what is the capital of France", "not sure")
check("", "type a question")

row = pd.DataFrame([{"id": 1, "status": "Open", "category": "Dirty water", "location": "Gate 2",
                     "severity": "High", "created_at": "2026-10-01", "admin_note": None}])
r = b.reply("status of SAN-0001", read=lambda *a, **k: row, parse=lambda t: 1, ticket=lambda i: "SAN-0001")
assert "Open" in r and "Gate 2" in r, r
r = b.reply("san 9", read=lambda *a, **k: row.iloc[0:0], parse=lambda t: 9, ticket=lambda i: "x")
assert "couldn't find" in r, r
print("all chatbot tests passed")
for q in ["wata", "Wata?", "hey wata", "hi Wata!", "WATA"]:
    assert "Wata" in b.reply(q), q
assert "Loss %" in b.reply("wata, how does the leakage check work?")
assert "20.0%" in b.reply("hey wata supplied 1000 billed 800")
assert b.reply("hello").startswith("Hey, I'm Wata")
print("wata name tests passed")
