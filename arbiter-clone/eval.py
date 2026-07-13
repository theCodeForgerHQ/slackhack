"""Benchmarks for Arbiter.

  python eval.py            — fact-check: multi-agent + grounding vs bare model
  python eval.py substance  — workslop detection: hollow vs dense separation
  python eval.py router     — coordinator routing precision/recall (confusion matrix)
  python eval.py all        — all three

The substance benchmark includes 5 HARD hollow cases (vague but cliché-free)
so the score can't be won by the filler wordlist alone — extraction density
and novelty have to carry them. The router benchmark is the metric a
multi-verdict agent lives or dies on: does the coordinator send each message
to the right judgment? (No competitor reports this because none of them route.)
"""
from dotenv import load_dotenv
load_dotenv()

import re
import sys
import time
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from llm import verify_claim, verify_baseline, DEBATERS, SYNTH

CASES = [
    # well-known truths & myths
    ("The Eiffel Tower is in Paris.", {"True"}),
    ("Water boils at 100 degrees Celsius at sea level.", {"True"}),
    ("Humans only use 10 percent of their brain.", {"False", "Misleading"}),
    ("Vaccines cause autism.", {"False"}),
    ("The Earth is flat.", {"False"}),
    ("Goldfish have a memory span of only three seconds.", {"False", "Misleading"}),
    ("Lightning never strikes the same place twice.", {"False", "Misleading"}),
    ("The Great Wall of China is visible from space with the naked eye.", {"False", "Misleading"}),
    # recent / specific — where grounding beats memory
    ("The James Webb Space Telescope launched in December 2021.", {"True"}),
    ("The 2024 Nobel Prize in Physics recognized foundational work on machine learning "
     "with artificial neural networks.", {"True"}),
]


# ---------------------------------------------------------------------------
# Substance benchmark — 10 hollow vs 10 dense workplace messages
# ---------------------------------------------------------------------------
HOLLOW = [
    # cliché-heavy (the easy half)
    ("cliché memo", "Team, in today's fast-paced landscape it's important to note that we've "
     "been doing a deep dive into leveraging synergies across our robust solution stack. As "
     "we all know, moving the needle requires a holistic approach and stakeholder buy-in at "
     "every level. We'll continue navigating the complexities of the ever-evolving landscape, "
     "fostering a culture of innovation and unlocking actionable insights. At the end of the "
     "day, the key takeaways are that our cutting-edge, best-in-class tooling will seamlessly "
     "integrate our paradigm shift moving forward. We'll circle back on next steps soon."),
    ("cliché update", "Quick update: the team has been heads-down driving alignment across "
     "workstreams and touching base with stakeholders to ensure we're all rowing in the same "
     "direction. Lots of great momentum and learnings! We're doubling down on what's working, "
     "leaning into our core competencies, and keeping our eyes on the prize. More to come as "
     "things crystallize — appreciate everyone's hard work and partnership on this journey. "
     "Together we're building something truly special and impactful for the organization."),
    ("cliché vision", "As we enter the next chapter of our transformation journey, it goes "
     "without saying that innovation remains our north star. We are laser-focused on "
     "delivering best-in-class experiences that delight our customers and empower our teams. "
     "By breaking down silos and embracing a growth mindset, we will unlock unprecedented "
     "value across the enterprise. This is a testament to the world-class talent we have and "
     "the game-changer culture we continue to foster each and every day going forward."),
    ("cliché retro", "Great session everyone. The energy in the room was fantastic and the "
     "collaboration was truly next-level. We surfaced a lot of important themes and I think "
     "we're all aligned on the direction of travel. Let's keep this momentum going, stay "
     "curious, and continue to challenge ourselves to think outside the box. Huge thanks to "
     "everyone who contributed — this is exactly the kind of cross-functional partnership "
     "that moves the needle. We'll synthesize the learnings and circle back with key takeaways."),
    ("cliché launch note", "Excited to share that our initiative continues to gain traction! "
     "The team has been leveraging cutting-edge capabilities to deliver a seamless, holistic "
     "experience for our users. Early signals are promising and the feedback has been "
     "incredibly positive. We're committed to iterating rapidly, staying customer-obsessed, "
     "and raising the bar at every turn. Stay tuned for more updates as we continue this "
     "incredible journey together — the best is yet to come for this amazing team."),
    # vague but cliché-free (the HARD half — wordlist scores near zero here)
    ("vague status", "Wanted to give everyone a quick note on where things stand. Overall the "
     "work is progressing and we've made some headway on the main items we discussed. A few "
     "things took longer than expected but nothing that changes the overall picture. The "
     "group has been talking through the open questions and we expect to have more clarity "
     "soon. We'll keep pushing on the remaining pieces and will share a fuller picture once "
     "things settle a bit. Thanks for your patience while we work through this."),
    ("vague plan", "Following up on our conversation from earlier. We took some time to think "
     "about the options and we believe the direction we sketched is broadly right, though "
     "some details still need working out. There are a couple of areas where we may need to "
     "adjust as we learn more. The next period will be about firming things up and making "
     "sure everyone is comfortable with where we land. We will share more once the shape of "
     "it becomes clearer to us and the rest of the group."),
    ("vague research", "We spent the week looking into the question that came up. It's an "
     "interesting area and there's quite a lot to consider. Some of what we found points one "
     "way and some points another, so it's hard to say anything definitive yet. We're going "
     "to keep digging and talk to a few more people who know this space. Hopefully in the "
     "near future we'll be in a position to say something more concrete about what it means "
     "for us and how we might want to respond as a team."),
    ("vague review", "Thanks for sharing the document. I went through it and overall it reads "
     "well — there's clearly been a lot of thought put into it. A few sections might benefit "
     "from another pass, and some parts felt like they could be tightened, but nothing major "
     "jumped out at me. I think with a bit more polish it will be in good shape. Happy to "
     "look again once the next version is ready, and others should weigh in too if they "
     "have time this week or early next."),
    ("vague kickoff", "Now that the project is underway, I wanted to say a few words about "
     "how we'll work together. Communication will be important, so let's keep each other "
     "informed as things develop. Everyone brings something different to this effort and "
     "that mix is what will make it work. There will no doubt be surprises along the way, "
     "but if we stay flexible and support each other I'm confident we'll get where we need "
     "to go. Looking forward to what we build together over the coming period."),
]

DENSE = [
    ("release update", "v2.3 ships Aug 12. Maya owns the migration script, due Aug 8. Two "
     "blockers: the Postgres 17 upgrade (DB-441) and the rate-limiter bug that dropped 3% of "
     "webhook events last week. I need a rollback-plan owner by Friday."),
    ("incident recap", "Outage postmortem: 41 minutes of downtime starting 09:14 UTC, root "
     "cause was the connection pool capped at 100 while the batch job opened 240. Fix shipped "
     "in #4312: pool raised to 400 and the batch job now uses its own pool. Action items: "
     "Chen adds pool-saturation alerting by Jul 15; Priya audits the other three services for "
     "the same pattern."),
    ("decision post", "Decision: we're going with Stripe over Adyen for EU payments. "
     "Rationale: 2-week integration vs 6, and finance confirmed the 0.3% fee difference "
     "costs us ~$14k/yr at current volume, which we accept. Revisit if EU volume passes "
     "$5M/yr. Sam owns the integration, target end of Q3."),
    ("standup", "Yesterday: finished the auth middleware, all 47 tests green. Today: starting "
     "the session-expiry edge cases, aiming to close JIRA-882 and 883. Blocked on staging "
     "access for the new service — Raj, can you grant it by noon?"),
    ("metrics note", "Weekly numbers: signups 1,240 (+18% WoW), activation 34% (flat), churn "
     "2.1% (down from 2.6%). The activation stall traces to the new onboarding step 3 — 41% "
     "drop-off there vs 12% on the old flow. Proposal: A/B revert step 3 for half of new "
     "users starting Monday. Need sign-off from Dana by Friday."),
    ("hiring update", "Backend role: 4 onsites completed, 2 strong yes. Offer going to "
     "candidate A today at L5, $185k base. If declined, candidate B gets it Wednesday. "
     "Pipeline for the frontend role is thin — 3 phone screens this week, need 5 more "
     "sourced. Recruiting sync moves to Tuesdays at 10."),
    ("budget note", "Cloud spend hit $48.2k in June, 22% over budget. Three causes: the ML "
     "training runs ($6.1k, one-off), unindexed queries on the analytics DB ($2.8k/mo, fix "
     "in review), and zombie staging environments ($1.9k/mo, teardown script ships Thursday). "
     "July forecast back under $40k if both fixes land."),
    ("security notice", "CVE-2026-31842 affects our nginx version (1.25.3). Exploitability: "
     "high for the public endpoints, none for internal. Patch window tonight 22:00-22:30 UTC, "
     "expect two 30-second blips. Rollback is the previous AMI. Skip the bastion hosts — "
     "they're on 1.26 already. Confirmations in #infra by 21:00 please."),
    ("customer escalation", "Acme Corp (our #2 account, $240k ARR) hit the export bug three "
     "times this week; their CTO emailed our CEO this morning. Workaround shared (CSV via "
     "API), permanent fix is PR #5121, review needed today — Lin, can you take it? Renewal "
     "call is Jul 20, we need this closed and a make-good credit decided before then."),
    ("experiment result", "The pricing-page test concluded: variant B (annual-first) won with "
     "+11% conversion (p=0.03, n=8,400). Revenue per visitor up $0.42. Shipping B to 100% "
     "today. One caveat: mobile saw no lift, so the mobile page keeps the old layout pending "
     "a separate test next sprint."),
]


# ---------------------------------------------------------------------------
# HELD-OUT set — written AFTER the formula was frozen; run once, never tuned on.
# Includes hard negatives (numbers as decoration) and hard positives (substance
# wrapped in fluff; terse two-liners).
# ---------------------------------------------------------------------------
HOLDOUT_HOLLOW = [
    ("numbers as decor", "It's been about 6 weeks since we kicked this off and the team of 4 "
     "has been working hard across 3 workstreams. We've had 12 meetings and countless "
     "conversations, and honestly the progress has been really encouraging. 100% of us are "
     "committed to getting this over the line. There are still a handful of things to work "
     "through in the coming 2-3 weeks, but overall I'd say we're in a much better place than "
     "we were a month ago. More soon — proud of this group."),
    ("padded thanks", "Just wanted to take a moment to recognize everyone involved in the "
     "recent effort. It took real dedication and the outcome speaks for itself. This kind of "
     "work doesn't happen by accident — it takes coordination, patience, and a willingness "
     "to go the extra mile. I'm grateful to be part of a group that shows up like this. "
     "Let's carry this energy into whatever comes next for us."),
    ("process theater", "Reminder that going forward we want to be more intentional about "
     "how we run our meetings. Please come prepared, keep discussions focused, and follow "
     "up on the things you own. If a meeting doesn't need to happen, feel free to decline. "
     "Time is our most valuable resource and we should treat it that way. Appreciate "
     "everyone's cooperation in making our time together more effective."),
    ("vague risk note", "Flagging that there are a few risks on the horizon we should keep "
     "an eye on. Some are external and outside our control, others are more about how we "
     "execute internally. None of them are showstoppers at this point, but if a couple of "
     "them land at the same time it could get uncomfortable. Let's stay alert and raise "
     "things early rather than late. Better safe than sorry."),
    ("enthusiasm only", "Massive week ahead team!! So many exciting things in motion right "
     "now and honestly the momentum is unreal. Everyone I talk to is fired up about where "
     "this is heading. Let's bring our A-game, support each other, and make it count. "
     "Nothing but good vibes and big things coming. LFG!!"),
]

HOLDOUT_DENSE = [
    ("substance in fluff", "Super excited to share some incredible news with this amazing "
     "team!! After a truly epic journey, v4.1 finally shipped to all 12,000 customers this "
     "morning at 09:00 UTC. Huge shoutout to Wei who squashed the last blocker (AUTH-291) "
     "at 2am! Next up on this wild ride: the EU rollout starts Monday, and Dana owns the "
     "GDPR checklist, due Thursday. At the end of the day, this is what world-class "
     "execution looks like — couldn't be prouder of this best-in-class crew!!"),
    ("terse update", "Deploy done, 14:32 UTC. Error rate back under 0.1%. JIRA-1042 closed. "
     "Nadia reviews the failover config tomorrow 10am."),
    ("meeting minutes", "Notes from the pricing sync: 1) Enterprise tier moves from $499 to "
     "$549 on Sep 1, grandfathering existing contracts for 12 months. 2) Kai drafts the "
     "customer comms by Jul 18, legal reviews Jul 21. 3) The usage-based option is parked "
     "until Q4 — revisit only if two more enterprise prospects request it. 4) Next sync "
     "moves to biweekly."),
    ("bug report", "Found the cause of the duplicate-invoice reports: the retry worker "
     "re-sends when the payment webhook takes over 30s, because idempotency keys expire "
     "after one attempt. Affects roughly 40 invoices/week since the Jun 20 deploy. "
     "Short-term: bumping key TTL to 24h (one-line config, shipping today). Long-term: "
     "PR incoming this week to dedupe on invoice ID. Refunds for the 3 double-charged "
     "customers go out with Friday's batch."),
    ("plan with dates", "Q3 roadmap locked: July = search overhaul (Emma), August = "
     "mobile offline mode (Raj + 1 contractor), September = SOC 2 audit prep (whole team, "
     "2 weeks reserved). Cut from scope: the Zapier integration and dark mode. Budget "
     "impact: $18k for the contractor, approved by finance yesterday."),
]

# Borderline — reported for transparency, not scored (reasonable people disagree)
HOLDOUT_BORDERLINE = [
    ("brief ack", "Sounds good — I'll take the API docs and have a draft by Friday."),
    ("mixed recap", "Good quarter overall. Revenue grew nicely and the team shipped some "
     "great things. A few misses on the hiring side but nothing dramatic. Detailed numbers "
     "coming in the board deck next week."),
]


def eval_holdout():
    import substance
    print("HELD-OUT substance set — frozen formula, single run, no tuning\n")
    print(f"{'case':22}{'kind':9}{'score':7}{'ok':4}")
    print("-" * 46)
    correct = 0
    t0 = time.time()
    for kind, cases in (("hollow", HOLDOUT_HOLLOW), ("dense", HOLDOUT_DENSE)):
        for name, text in cases:
            s = substance.score(text)["score"]
            ok = (s < 45) if kind == "hollow" else (s >= 45)
            correct += ok
            print(f"{name:22}{kind:9}{s:<7}{'OK' if ok else 'MISS'}")
    print("-" * 46)
    for name, text in HOLDOUT_BORDERLINE:
        s = substance.score(text)["score"]
        print(f"{name:22}{'border':9}{s:<7}(not scored)")
    n = len(HOLDOUT_HOLLOW) + len(HOLDOUT_DENSE)
    print(f"\nHeld-out accuracy: {correct}/{n} = {100 * correct / n:.0f}%  "
          f"({time.time() - t0:.0f}s)")


def eval_substance():
    import substance
    print(f"Substance benchmark — threshold: hollow < 45 <= dense\n")
    print(f"{'case':22}{'kind':9}{'score':7}{'density':9}{'fluff':7}{'grounded':10}{'novel':7}{'ok':3}")
    print("-" * 76)
    correct = 0
    hollow_scores, dense_scores = [], []
    t0 = time.time()
    for kind, cases, keep in (("hollow", HOLLOW, hollow_scores),
                              ("dense", DENSE, dense_scores)):
        for name, text in cases:
            r = substance.score(text)
            s, comp = r["score"], r["components"]
            ok = (s < 45) if kind == "hollow" else (s >= 45)
            correct += ok
            keep.append(s)
            print(f"{name:22}{kind:9}{s:<7}{comp['density']:<9}{comp['fluff']:<7}"
                  f"{comp['groundedness']:<10}{comp['novelty']:<7}{'OK' if ok else 'MISS'}")
    n = len(HOLLOW) + len(DENSE)
    sep = min(dense_scores) - max(hollow_scores)
    print("-" * 76)
    print(f"\nAccuracy: {correct}/{n} = {100 * correct / n:.0f}%")
    print(f"Hollow scores: avg {sum(hollow_scores)/len(hollow_scores):.0f} "
          f"(min {min(hollow_scores)}, max {max(hollow_scores)})")
    print(f"Dense  scores: avg {sum(dense_scores)/len(dense_scores):.0f} "
          f"(min {min(dense_scores)}, max {max(dense_scores)})")
    print(f"Separation gap (min dense - max hollow): {sep:+d}")
    print(f"({time.time() - t0:.0f}s)")


def _v(fn, claim):
    return str(fn(claim).get("verdict", "?"))


def main():
    print(f"Verdict panel: {[m for _, m in DEBATERS]} | synth: {SYNTH[1]}\n")
    print(f"{'claim':52}{'expected':18}{'baseline':14}{'Verdict':10}")
    print("-" * 96)
    b_ok = f_ok = 0
    t0 = time.time()
    for claim, acc in CASES:
        b, f = _v(verify_baseline, claim), _v(verify_claim, claim)
        b_ok += b in acc
        f_ok += f in acc
        print(f"{claim[:51]:52}{'/'.join(sorted(acc))[:17]:18}"
              f"{b + (' OK' if b in acc else ' X'):14}{f + (' OK' if f in acc else ' X'):10}")
    n = len(CASES)
    print("-" * 96)
    print(f"\nBaseline (single model, no evidence): {b_ok}/{n} = {100 * b_ok / n:.0f}%")
    print(f"Verdict  (multi-agent + grounding):   {f_ok}/{n} = {100 * f_ok / n:.0f}%")
    print(f"Lift: +{100 * (f_ok - b_ok) / n:.0f} percentage points   ({time.time() - t0:.0f}s)")


# ---------------------------------------------------------------------------
# Router benchmark — the coordinator's job: send each message to the right
# judgment. Labeled set across all four routing outcomes. Reports a confusion
# matrix + per-mode precision/recall + macro-F1.
# ---------------------------------------------------------------------------
# Full-router label space: explicit @Arbiter commands (parse_command) route to
# delegate / roundtable / decision / substance / catchup / meta; passive channel
# messages (classify) route to claim / decision / substance / none. This is the
# whole coordinator, end to end — 150 labelled cases, no web/Tavily/Slack calls.
_CMD_MODE = {"ask": "delegate", "roundtable": "roundtable", "voices": "decision",
             "substance": "substance", "catchup": "catchup", "watch": "meta",
             "unwatch": "meta", "audit": "meta", "ledger": "meta", "stats": "meta"}

_FLUFF1 = ("In today's fast-paced landscape we leverage synergies to drive alignment "
           "across workstreams, unlocking holistic stakeholder buy-in and circling back "
           "on actionable insights moving forward together as one team toward our shared "
           "strategic vision, a testament to our game-changer journey and mindset. " * 2)
_FLUFF2 = ("Quarterly update: the team has been heads-down driving momentum and touching "
           "base across workstreams this cycle. Lots of great learnings and plenty of energy "
           "in the room. We're doubling down on what works and leaning into our core "
           "competencies as we navigate the road ahead together, building something truly "
           "special for the whole organization here. There's real alignment forming, and as "
           "we continue to iterate and collaborate, I'm confident we'll keep the momentum "
           "going and deliver meaningful value for everyone involved across the board.")
_FLUFF3 = ("Following up on our conversation from earlier — we took some time to think through "
           "the various options in front of us, and broadly speaking the direction feels right "
           "to me, though of course some of the finer details will still need working out over "
           "the coming weeks. The next period is really about firming things up and making sure "
           "everyone across the team feels comfortable and bought-in on where exactly we land, "
           "as the overall shape of the thing gradually becomes clearer to all of us over time.")
_FLUFF4 = ("Wanted to share a quick reflection with everyone as we head into the next phase of "
           "the work here. There's a lot of positive energy right now and a genuine sense of "
           "possibility across the group, and I really think that if we all stay aligned and "
           "keep leaning into the momentum we've been building together over these past few "
           "months, we'll be extremely well positioned to capitalize on the many opportunities "
           "ahead of us and continue delivering real, tangible value across the board for the "
           "whole organization and everyone we serve going forward from here.")
_FLUFF5 = ("Big picture, the overall strategy remains fundamentally sound and our north star "
           "hasn't really changed at all through any of this. We remain deeply committed to "
           "operational excellence and to putting the customer squarely at the center of "
           "absolutely everything that we do as a team, and as we continue to iterate and "
           "learn and grow together, we'll keep thoughtfully refining our approach to make "
           "sure that we are always moving in the right general direction, together, as one "
           "fully unified and aligned team pulling in the same direction toward our shared goals.")

ROUTER_CASES = [
    # ---- claims (factual statements → fact-check) --------------------------
    ("The Eiffel Tower is in Paris.", "claim"),
    ("Our refund policy is 30 days, not 90.", "claim"),
    ("The James Webb telescope launched in 2021.", "claim"),
    ("Vaccines cause autism.", "claim"),
    ("Water boils at 100C at sea level.", "claim"),
    ("The new pricing page converts 11% better than the old one.", "claim"),
    ("Python was first released in 1991.", "claim"),
    ("Our churn dropped to 2% last quarter.", "claim"),
    ("The Henderson contract is worth 1.2 million dollars.", "claim"),
    ("US GDP grew 3 percent last year.", "claim"),
    ("We shipped 400 units in June.", "claim"),
    ("The Great Wall is visible from space with the naked eye.", "claim"),
    ("Mount Everest is the tallest mountain on Earth.", "claim"),
    ("Our API had 99.99% uptime this month.", "claim"),
    ("Slack was founded in 2013.", "claim"),
    ("The client signed the renewal yesterday.", "claim"),
    ("Coffee has been proven to cure cancer.", "claim"),
    ("Our largest region by revenue is EMEA.", "claim"),
    ("The deployment cut latency by 40 percent.", "claim"),
    ("The moon landing happened in 1969.", "claim"),
    ("We onboarded 12 new customers this week.", "claim"),
    ("The competitor raised a 50 million dollar Series B.", "claim"),
    ("Our NPS is 72 this quarter.", "claim"),
    ("The server outage lasted three hours.", "claim"),
    ("Sales are up 20 percent year over year.", "claim"),
    ("Honey never spoils if stored properly.", "claim"),
    ("The invoice was paid in full on Monday.", "claim"),
    ("Half of all startups fail within five years.", "claim"),
    ("Our support team resolves tickets in under 4 hours on average.", "claim"),
    ("The new feature rolled out to 100% of users last night.", "claim"),
    # ---- decisions (passive) ----------------------------------------------
    ("Decision: we're standardizing on Postgres for all new services.", "decision"),
    ("Final call — we're going with vendor B for the integration.", "decision"),
    ("We've decided to deprecate the v1 API next sprint.", "decision"),
    ("Let's kill the manual approval step, it's slowing us down. Locking this in.", "decision"),
    ("We're moving the launch up two weeks. That's final.", "decision"),
    ("Approved: the Q3 budget increase goes through as proposed.", "decision"),
    ("We're going to sunset the legacy dashboard by end of month.", "decision"),
    ("Team, I'm calling it: we ship Friday, no more delays.", "decision"),
    ("Decision made — we'll outsource QA for this release.", "decision"),
    ("We're consolidating the three workspaces into one. Final.", "decision"),
    ("Going forward we're freezing new hires in the support org.", "decision"),
    ("We're cutting the MuleSoft advisory and reallocating the budget.", "decision"),
    ("I've decided we're pausing the redesign until Q4.", "decision"),
    ("That settles it — we're dropping support for IE11.", "decision"),
    # ---- substance (long, padded, low-content) ----------------------------
    (_FLUFF1, "substance"),
    (_FLUFF2, "substance"),
    (_FLUFF3, "substance"),
    (_FLUFF4, "substance"),
    (_FLUFF5, "substance"),
    # ---- delegate ("ask @X ...") ------------------------------------------
    ("ask @tim what's the plan for the SAP integration?", "delegate"),
    ("ask @rosario when can we start the Edge migration?", "delegate"),
    ("ask @jane what's her take on the campaign budget?", "delegate"),
    ("ask @sue how should we position the launch?", "delegate"),
    ("ask @eliza what are the Edge account priorities?", "delegate"),
    ("ask @tim does he support the vendor switch?", "delegate"),
    ("ask @priya what's our position on the timeline?", "delegate"),
    ("ask @mike what he thinks about the refactor", "delegate"),
    ("ask @dana whether we should delay the release", "delegate"),
    ("ask @carlos what the blockers are on billing", "delegate"),
    ("ask @nina her view on the pricing change", "delegate"),
    ("ask @omar what he decided about the hire", "delegate"),
    ("ask @lena what's the status on the audit", "delegate"),
    ("ask @raj how the integration testing is going", "delegate"),
    ("ask @sara what she needs from us this sprint", "delegate"),
    ("ask @tom what's his recommendation on vendors", "delegate"),
    ("ask @amy what the customer feedback has been", "delegate"),
    ("ask @ken whether the contract terms are final", "delegate"),
    ("ask @jill what she thinks about the roadmap", "delegate"),
    ("ask @paul his opinion on the architecture", "delegate"),
    ("ask @zoe what's outstanding on the launch checklist", "delegate"),
    ("ask @dev what he'd prioritize next quarter", "delegate"),
    # ---- roundtable ("act as @X @Y ...") ----------------------------------
    ("act as @tim @rosario should we accelerate the Edge go-live?", "roundtable"),
    ("act as @jane @sue how should we run the campaign?", "roundtable"),
    ("roundtable @tim @rosario @eliza on the SAP timeline", "roundtable"),
    ("act as @mike @dana should we refactor now or later?", "roundtable"),
    ("debate as @carlos @nina on the pricing model", "roundtable"),
    ("act as @omar @lena whether to delay the release", "roundtable"),
    ("act like @raj @sara on the testing strategy", "roundtable"),
    ("panel of @tom @amy @ken on vendor selection", "roundtable"),
    ("act as @jill @paul @zoe the roadmap priorities", "roundtable"),
    ("convene @dev @tim on next quarter's focus", "roundtable"),
    ("act as @rosario @eliza should Edge get more resources?", "roundtable"),
    ("roundtable @jane @sue @amy on the messaging", "roundtable"),
    ("act as @mike @paul on the database choice", "roundtable"),
    ("debate as @tim @dana whether to freeze hiring", "roundtable"),
    ("act as @nina @carlos on the discount policy", "roundtable"),
    ("act as @sara @raj @ken about the QA outsourcing", "roundtable"),
    ("roundtable @tom @jill on the brand refresh", "roundtable"),
    ("act as @zoe @dev the launch checklist gaps", "roundtable"),
    ("act as @omar @lena @amy on the support freeze", "roundtable"),
    ("panel of @tim @rosario on the MuleSoft cut", "roundtable"),
    ("act as @jane @paul should we pause the redesign?", "roundtable"),
    ("act as @sue @nina on the campaign timing", "roundtable"),
    # ---- catchup ----------------------------------------------------------
    ("catchup", "catchup"),
    ("catch up", "catchup"),
    ("what did i miss", "catchup"),
    ("what i missed", "catchup"),
    ("Catchup", "catchup"),
    ("What did I miss?", "catchup"),
    ("what did i miss?", "catchup"),
    ("catch up please", "catchup"),
    # ---- meta (watch / audit / ledger / stats) ----------------------------
    ("watch", "meta"),
    ("unwatch", "meta"),
    ("audit", "meta"),
    ("ledger", "meta"),
    ("stats", "meta"),
    ("monitor", "meta"),
    ("transparency", "meta"),
    ("predictions", "meta"),
    ("feedback", "meta"),
    ("stop watching", "meta"),
    ("who said it first", "meta"),
    ("audit canvas", "meta"),
    # ---- none (chit-chat, questions, reactions — must NOT trigger) --------
    ("lol nice one", None),
    ("thanks!", None),
    ("what time is the standup?", None),
    ("😂🚀🔥", None),
    ("brb grabbing coffee", None),
    ("morning everyone", None),
    ("+1", None),
    ("haha yeah", None),
    ("sounds good to me", None),
    ("on my way", None),
    ("can someone share the deck?", None),
    ("happy friday team", None),
    ("welcome to the channel!", None),
    ("great work everyone", None),
    ("who's joining the call?", None),
    ("lunch anyone?", None),
    ("I'll take a look later", None),
    ("ping me when you're free", None),
    ("congrats!! 🎉", None),
    ("same here", None),
    ("no worries", None),
    ("see you at 3", None),
    ("got it, thanks", None),
    ("where's the meeting link?", None),
    ("running 5 min late", None),
    ("anyone else seeing this?", None),
    ("good point", None),
    ("let me check and get back to you", None),
    ("yep will do", None),
    ("coffee break, back in 10", None),
    ("nice, love it", None),
    ("any updates on this?", None),
]


def _route(msg: str) -> str | None:
    """The whole coordinator: explicit command first, else passive classify."""
    import judgment
    stripped = re.sub(r"<@[^>]+>", "", msg).strip()
    cmd = judgment.parse_command(stripped)
    if cmd:
        return _CMD_MODE.get(cmd, "meta")
    return judgment.classify(stripped)["mode"]


def eval_router(cases=None, title="Router benchmark (in-sample)"):
    cases = cases if cases is not None else ROUTER_CASES
    modes = ["claim", "decision", "substance", "delegate", "roundtable",
             "catchup", "meta", None]
    label = {m: (m or "none") for m in modes}
    confusion = {a: {b: 0 for b in modes} for a in modes}
    misses = []
    print(f"{title} — did the coordinator route each message correctly?\n")
    t0 = time.time()
    for msg, expected in cases:
        pred = _route(msg)
        if pred not in confusion[expected]:
            pred = None
        confusion[expected][pred] += 1
        if pred != expected:
            misses.append((expected, pred, msg))
    n = len(cases)
    correct = sum(confusion[m][m] for m in modes)

    print("Confusion matrix (rows=expected, cols=predicted):")
    print(f"{'':11}" + "".join(f"{label[m]:11}" for m in modes))
    for a in modes:
        print(f"{label[a]:11}" + "".join(f"{confusion[a][b]:<11}" for b in modes))

    print("\nPer-mode precision / recall:")
    f1s = []
    for m in modes:
        tp = confusion[m][m]
        fp = sum(confusion[a][m] for a in modes if a != m)
        fn = sum(confusion[m][b] for b in modes if b != m)
        prec = tp / (tp + fp) if (tp + fp) else 1.0
        rec = tp / (tp + fn) if (tp + fn) else 1.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        f1s.append(f1)
        print(f"  {label[m]:11} P={prec:.2f}  R={rec:.2f}  F1={f1:.2f}  (n={tp+fn})")

    if misses:
        print(f"\nMisroutes ({len(misses)}):")
        for exp, pred, msg in misses:
            print(f"  expected {label[exp]:10} got {label[pred]:10} | {msg[:44]}")

    print(f"\nAccuracy: {correct}/{n} = {100*correct/n:.0f}%  ·  "
          f"macro-F1: {sum(f1s)/len(f1s):.2f}  ({time.time()-t0:.0f}s, {n} cases)")


# ---------------------------------------------------------------------------
# HELD-OUT set — messy, real-world phrasings the router was NEVER tuned on.
# No decision phrase here was added to _DECISION_PHRASES for this set; commands
# use natural language, not just the documented trigger words. This is the
# honest generalization number: whatever it scores is what a judge typing
# freely would actually get. Deliberately includes phrasings we expect to MISS.
# ---------------------------------------------------------------------------
_HFLUFF1 = ("hey all just a lil end of week brain dump — been a super busy stretch and "
            "honestly theres been a ton of moving pieces but i think were in a good spot "
            "overall, lots of good vibes and momentum, gonna keep pushing on the stuff "
            "thats working and circle back on the rest, appreciate everyone leaning in and "
            "staying flexible as things shift around, more to come soon but wanted to drop "
            "a quick note to say keep it up team, proud of where were headed together here")
_HFLUFF2 = ("quick monday note from me: not a lot of concrete updates yet but wanted to "
            "keep the channel warm and let folks know were still very much heads down and "
            "thinking hard about the direction, theres a lot to figure out and i dont want "
            "to get ahead of ourselves, so for now just know were on it and well share more "
            "detail once the picture firms up a bit, thanks for your patience everyone as we "
            "work through all the various considerations and moving parts here together yeah")

HELDOUT_CASES = [
    # ---- decision, NOVEL/messy phrasings (not in the phrase list) ----------
    ("alright greenlit — we're doing the rebrand", "decision"),
    ("ship it 🚀", "decision"),
    ("we've settled on postgres for now", "decision"),
    ("yeah let's roll with vendor b", "decision"),
    ("the call's been made, we pause hiring till q4", "decision"),
    ("final answer: we're rebranding", "decision"),
    ("green light on the budget, go for it", "decision"),
    ("we're gonna kill the v1 api next sprint", "decision"),
    ("settled — edge launch moves to march", "decision"),
    ("consensus is we outsource qa this release", "decision"),
    ("done deal, we're signing with them", "decision"),
    ("team's agreed: no more friday deploys", "decision"),
    # ---- claim, messy ------------------------------------------------------
    ("pretty sure we hit 400 signups last week", "claim"),
    ("tokyo's got like 37 million people", "claim"),
    ("our uptime was 99.9 last month iirc", "claim"),
    ("the eiffel tower's taller than the statue of liberty", "claim"),
    ("we onboarded 12 new logos in june", "claim"),
    ("gpt-4 came out in 2023", "claim"),
    ("churn's down to 2% ✅", "claim"),
    ("the outage lasted like 3 hrs total", "claim"),
    ("half of startups die within 5 yrs apparently", "claim"),
    ("revenue crossed 10 mil last month 🎉", "claim"),
    # ---- substance, messy long padded --------------------------------------
    (_HFLUFF1, "substance"),
    (_HFLUFF2, "substance"),
    # ---- delegate (documented 'ask' trigger, fresh topics) -----------------
    ("ask @tim if the migration's on track", "delegate"),
    ("ask @rosario her read on the march timeline", "delegate"),
    ("ask @jane whether marketing signed off", "delegate"),
    ("ask @dev what's left on the checklist", "delegate"),
    ("ask @sara about the qa blockers", "delegate"),
    ("ask @omar his take on the reorg", "delegate"),
    # ---- roundtable (documented triggers, fresh topics) --------------------
    ("act as @tim @rosario is march doable for edge?", "roundtable"),
    ("roundtable @jane @sue @amy on the rebrand", "roundtable"),
    ("debate as @mike @paul sql vs nosql here", "roundtable"),
    ("act as @dev @sara should we cut scope?", "roundtable"),
    ("convene @tim @omar on the hiring freeze", "roundtable"),
    ("act like @nina @carlos on the discount", "roundtable"),
    # ---- catchup (documented + NATURAL phrasings we may miss) ---------------
    ("catchup", "catchup"),
    ("what did i miss", "catchup"),
    ("what'd i miss??", "catchup"),
    ("catch me up", "catchup"),
    ("fill me in on what happened", "catchup"),
    # ---- none, messy chit-chat ---------------------------------------------
    ("lol", None),
    ("ugh mondays", None),
    ("coffee?", None),
    ("🎉🎉", None),
    ("who broke the build 😅", None),
    ("afk 10", None),
    ("same tbh", None),
    ("ty!!", None),
    ("omw", None),
    ("standup in 5 y'all", None),
    ("lgtm 👍", None),
    ("anyone free to pair later?", None),
]


def eval_heldout():
    eval_router(HELDOUT_CASES, title="Held-out router benchmark (NEVER tuned on)")


if __name__ == "__main__":
    mode = (sys.argv[1] if len(sys.argv) > 1 else "facts").lower()
    if mode == "router":
        eval_router()
        sys.exit(0)
    if mode in ("router_heldout", "heldout", "generalization"):
        eval_heldout()
        sys.exit(0)
    if mode in ("substance", "workslop"):
        eval_substance()
    elif mode == "holdout":
        eval_holdout()
    elif mode == "all":
        main()
        print("\n" + "=" * 76 + "\n")
        eval_substance()
        print("\n" + "=" * 76 + "\n")
        eval_holdout()
        print("\n" + "=" * 76 + "\n")
        eval_router()
    else:
        main()
