# Failure Recovery Skill

Use after a failed patch, failed PR review, failed runtime validation, or UI regression.

Return:
- what failed
- whether this is first failure or repeated failure
- updated severity classification
- root cause hypothesis
- missing test/evidence that would have caught it
- recommended next move: small follow-up, full plumbing analysis, or split plan

Rules:
- after one failed patch, reclassify
- after two related patches, stop patching and move to full plumbing analysis or split plan
- do not patch UI when backend/API contract is wrong
- do not patch backend when frontend mapper dropped valid fields
- do not claim runtime success without runtime evidence
