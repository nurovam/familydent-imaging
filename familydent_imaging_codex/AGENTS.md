# FamilyDent Imaging — repository guidance for Codex

## Mission
Develop FamilyDent Imaging MVP according to `docs/TECH_SPEC.md`. This is a security-sensitive medical-image sharing system. Design is sourced from the user's existing OpenDesign/Hallmark project, **not** generated from scratch.

## Before making changes
1. Read `docs/TECH_SPEC.md`, this file, repo structure and any nested AGENTS.md.
2. Locate design handoff (`DESIGN.md`, `SKILL.md`, design tokens, staged exports/assets); preserve brand and implemented UI. If missing, document blocker; never fabricate designs.
3. Follow `docs/IMPLEMENTATION_PLAN.md` once created. Start only the explicitly requested phase.
4. Avoid touching production services, real databases, real DICOM, real clinic network or live Mailcow without explicit approval.

## Non-negotiable security
- Patient authorization is **per study grant**, not patient-wide history.
- Patient flow = verified contact email + fresh email OTP + independent secret physically issued after identity verification.
- Do not merge by full name/email; no self-service recovery on email alone.
- Doctors must see only explicitly assigned studies; MFA for doctor/staff/admin.
- Backend must check every API, DICOMweb, download and Range request. Revoke active sessions when grant is revoked.
- No public Orthanc/NAS/PostgreSQL, no international proxy carrying DICOM, no external telemetry or CDN for medical data.
- Never log raw OTP, card codes, access tokens, credentials, DICOM payload or identity document copies.
- Germany-hosted Mailcow: neutral notices and email OTP only; no medical details or access-grant URLs.
- Disabled by default: irreversible deletion of medical data; Romexis Viewer bundling until license confirmed; live SMTP/prod deployment.
- Only synthetic/anonymized research data in dev and CI.

## Engineering rules
- Reuse existing repo stack when compatible. Proposed stack: React/Next.js frontend, FastAPI, PostgreSQL/Alembic, Orthanc/DICOMweb/OHIF, background workers, Docker Compose for local development.
- Add typing, migrations, tests and docs with each feature. Use secure defaults, `.env.example` (no real secrets), least privilege, rate limits and audit.
- Deliver phases with tests, security-relevant edge cases and explicit limitations.
- Before proceeding to the next phase, report changes, proof of tests, remaining risks, and request a new explicit task.
- Never claim production compliance or readiness without legal, licensing, security and operational review.
