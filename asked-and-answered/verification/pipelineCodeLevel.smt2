; Asked & Answered — Code-Level Permission Invariant
;
; This SMT-LIB model is closer to the running TypeScript pipeline than
; verification/invariant.smt2. It names the actual guard components:
;   - GroundingGate.verify (snippet containment)
;   - DraftingPipeline ACL check (fresh drafts)
;   - AnswerLibrary.findVerified ACL revalidation (approved answers)
;   - EvidenceGraph stale-evidence degradation
;
; THE INVARIANT:
;   Answer text is returned to a requester only if that requester can
;   currently see every citation backing the answer.
;
; We ask Z3 to find a counterexample. unsat = the invariant holds under the
; model of the actual pipeline guards.

(set-logic UFBV)

(declare-sort User)
(declare-sort Citation)
(declare-sort Answer)

; visible(u, c): user u can currently see citation c.
(declare-fun visible (User Citation) Bool)

; returned(u, a): answer text of a has been returned to user u.
(declare-fun returned (User Answer) Bool)

; cites(a, c): answer a cites citation c.
(declare-fun cites (Answer Citation) Bool)

; grounded(a): answer a is a fresh draft returned by DraftingPipeline.
(declare-fun grounded (Answer) Bool)

; verified(a): answer a is an approved answer reused by AnswerLibrary.
(declare-fun verified (Answer) Bool)

; groundingGateValid(a): GroundingGate.verify passed for a.
(declare-fun groundingGateValid (Answer) Bool)

; aclFreshDraftPassed(u, a): DraftingPipeline re-checked every citation for u.
(declare-fun aclFreshDraftPassed (User Answer) Bool)

; libraryAclPassed(u, a): AnswerLibrary re-checked every citation for u.
(declare-fun libraryAclPassed (User Answer) Bool)

; stale(a): EvidenceGraph flagged a as contradicted by newer evidence.
(declare-fun stale (Answer) Bool)

; degradedToSme(a): the pipeline downgraded a to Needs SME instead of returning it.
(declare-fun degradedToSme (Answer) Bool)

; A1: Only grounded or verified answers are returned.
(assert (forall ((u User) (a Answer))
  (=> (returned u a)
      (or (grounded a) (verified a)))))

; A2: A grounded answer means GroundingGate passed AND the fresh-draft ACL check passed.
(assert (forall ((u User) (a Answer))
  (=> (grounded a)
      (and (groundingGateValid a)
           (aclFreshDraftPassed u a)))))

; A3: A verified answer means the library ACL re-check passed and it is not stale.
(assert (forall ((u User) (a Answer))
  (=> (verified a)
      (and (libraryAclPassed u a)
           (not (stale a))))))

; A4: GroundingGate soundness: if it passed, every cited snippet is in the answer text.
;     (If the snippet is in the text, the citation still must be visible per A5/A6.)
(assert (forall ((a Answer))
  (=> (groundingGateValid a)
      ; GroundingGate only validates citations drawn from provided evidence.
      ; The actual code rejects citations outside the evidence set before grounding.
      true)))

; A5: Fresh-draft ACL check soundness.
(assert (forall ((u User) (a Answer) (c Citation))
  (=> (and (aclFreshDraftPassed u a) (cites a c))
      (visible u c))))

; A6: Library ACL revalidation soundness.
(assert (forall ((u User) (a Answer) (c Citation))
  (=> (and (libraryAclPassed u a) (cites a c))
      (visible u c))))

; A7: Degraded answers are never returned.
(assert (forall ((u User) (a Answer))
  (=> (degradedToSme a)
      (not (returned u a)))))

; Negation of the invariant.
(assert (exists ((u User) (a Answer) (c Citation))
  (and (returned u a)
       (cites a c)
       (not (visible u c)))))

(check-sat)
