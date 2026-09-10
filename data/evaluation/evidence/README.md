# Evidence Preservation Policy and Compliance Protocol
**Project:** IT Job Market Intelligence Tool (J26_SE_355)  
**Location:** `data/evaluation/evidence/`  

---

## 1. Evidence Preservation Principles

To ensure quantitative reproducibility without violating copyright or data privacy laws:
1. **Primary Evidence:** The original web page at collection time is the ground truth.
2. **Permitted Snapshots:** Minimal sanitized text DOM representations and structured API payloads are archived for audit purposes.
3. **Privacy Sanitization:** Direct contact information (recruiter personal mobile numbers, personal email addresses) is stripped prior to artifact storage.
4. **Terms of Service Compliance:** Evidence capture respects robots.txt restrictions, polite crawling delays, and portal access policies.

## 2. Disappearing and Ephemeral Pages

Job postings are inherently ephemeral. When an advertisement is removed:
- Evaluators **must never fabricate** or estimate expected values.
- If a valid snapshot was archived prior to removal, the snapshot serves as verifiable evidence.
- If no snapshot exists and the page is 404/expired, the affected fields must be annotated as `unavailable` or `ambiguous` with explicit audit notes.
