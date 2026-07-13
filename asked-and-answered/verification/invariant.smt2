; Asked & Answered — Permission Invariant SMT-LIB Spec
;
; THE INVARIANT:
;   Answer text is returned to a requester only if that requester can
;   currently see every citation backing the answer.
;
; This model abstracts the pipeline to two safety-critical properties:
;   1. RETURN-GUARD: before any answer is returned, the pipeline checks
;      visibility for every citation backing that answer.
;   2. CHECKER-SOUND: the visibility check never reports "can see" when the
;      requester actually cannot see the citation.
;
; We ask Z3 to find a counterexample to the invariant assuming (1) and (2).
; If the result is unsat, the invariant is formally entailed by the guard
; and the sound checker.

(set-logic UFBV)

(declare-sort User)
(declare-sort Citation)
(declare-sort Answer)

; visible(u, c): user u can currently see citation c.
(declare-fun visible (User Citation) Bool)

; returned(u, a): answer a has been returned to user u.
(declare-fun returned (User Answer) Bool)

; cites(a, c): answer a cites citation c.
(declare-fun cites (Answer Citation) Bool)

; checked(u, c): the pipeline has verified that u can see c.
(declare-fun checked (User Citation) Bool)

; RETURN-GUARD: returned => every citation checked.
(assert (forall ((u User) (a Answer))
  (=> (returned u a)
      (forall ((c Citation))
        (=> (cites a c) (checked u c))))))

; CHECKER-SOUND: checked => actually visible.
(assert (forall ((u User) (c Citation))
  (=> (checked u c) (visible u c))))

; Negation of the invariant: a returned answer cites an invisible citation.
(assert (exists ((u User) (a Answer) (c Citation))
  (and (returned u a)
       (cites a c)
       (not (visible u c)))))

(check-sat)
