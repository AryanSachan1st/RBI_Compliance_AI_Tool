# Curated regulatory sources

This repository includes the currently available public source PDFs in
`storage/regulatory_sources/`. They are included for the RAG corpus only and
must not be used to set deterministic thresholds until a rule owner reviews
and approves the cited clauses.

## Included

- RBI (Commercial Banks - Interest Rates on Advances) Directions, 2025
- RBI (NBFC - Credit Facilities) Directions, 2025
- IRDAI Insurance Fraud Monitoring Framework Guidelines (supplemental only)

## Required downloads before claiming full BRD coverage

- RBI (Digital Lending) Directions, 2025 — RBI/2025-26/36,
  DOR.STR.REC.19/21.07.001/2025-26, dated 8 May 2025.
- IRDAI (Protection of Policyholder's Interests, operations and allied matters
  of insurers) Regulations, 2024 — IRDAI/Reg/11/205/2024.
- IRDAI Master Circular on Protection of Policyholders' Interests, 2024 —
  IRDAI/PP&GR/CIR/MISC/117/9/2024.

After downloading an approved PDF, place it in `storage/regulatory_sources/`,
add its metadata to `storage/regulatory_sources.json`, and start the API once
to generate `storage/regulatory_chunks.json`.
