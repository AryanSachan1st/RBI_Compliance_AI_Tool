# Ground Truth Answer Key — synthetic_test_loan_document.md

Use this to check your pipeline's output against known-correct verdicts. Do NOT feed this
file into the extractor — it's for your validation only.

| Clause | Expected Verdict | Why |
|---|---|---|
| 1. Loan Amount and Purpose | **Compliant** | Straightforward disclosure, no issue. |
| 2. Rate of Interest | **Compliant** | Discloses rate basis (reducing balance) and EMI clearly. |
| 3. Processing and Other Charges | **Compliant** | Fees itemized upfront. |
| 4. Prepayment and Foreclosure | **NON-COMPLIANT** | KFS rules (RBI KFS circular, April 2024) require ALL charges — including foreclosure/prepayment charges — to be disclosed upfront in the KFS itself, not deferred to "at the time of closure, at the Bank's discretion." This is a classic transparency violation: the borrower cannot compare true cost of credit without knowing this in advance. **Should retrieve:** clauses on fee/charge disclosure requirements from the Credit Facilities / Interest Rates on Advances directions in your corpus. |
| 5. Right to Recall / Rate Revision | **NON-COMPLIANT** | RBI's Interest Rates on Advances directions require banks to intimate borrowers of any change in interest rate, EMI, or tenure — "without prior notice" directly contradicts the notice/intimation requirement. This is the most clear-cut violation in the document. **Should retrieve:** clauses on interest rate reset / borrower intimation from the Interest Rates on Advances direction in your corpus. |
| 6. KYC and Documentation | **Compliant** | Straightforward list, matches standard KYC document requirements. |
| 7. Total Cost of Credit | **Compliant** | APR-equivalent (all-inclusive cost) is disclosed as required by KFS rules. |
| 8. Grievance Redressal | **NON-COMPLIANT** | This is deliberately vague and incomplete: it gives a phone number but omits (a) a defined resolution timeline, (b) escalation path to a Nodal Officer / Principal Nodal Officer, and (c) the right to escalate to the RBI Internal Ombudsman / Banking Ombudsman Scheme if unresolved. Your corpus's Internal Ombudsman Directions and the "Redressal of grievances" clauses (e.g. Clause 84 in the Credit Card directions, Clause 13 in the Internal Ombudsman direction) specify this structured escalation requirement. **Should retrieve:** exactly those grievance/ombudsman clauses — this is the best test of whether your retrieval step finds the right guideline given a vague real-world clause. |
| 9. Insurance | **Compliant** | Explicitly states insurance is optional and not tied to loan sanction — this itself reflects a real RBI requirement (no forced bundling of insurance with loans), so this clause is compliant *because* it correctly avoids a common violation. |
| 10. Governing Law | **Compliant / Not Applicable** | Standard boilerplate, not something your compliance corpus would have an opinion on. Good test of whether your judgment step correctly says "not applicable" instead of forcing a verdict. |

## Summary
- **3 deliberate violations:** Clause 4 (foreclosure disclosure), Clause 5 (rate change notice), Clause 8 (grievance escalation).
- **1 "trap" compliant clause:** Clause 9, to check the system doesn't over-flag things that sound risky (insurance) but are actually handled correctly.
- **1 "not applicable" clause:** Clause 10, to check the system doesn't force a compliance verdict on generic legal boilerplate that isn't covered by RBI/IRDAI regulations.

If your pipeline flags roughly these clauses and lets the others pass, the end-to-end extraction → retrieval → judgment loop is working.
