# Cabinet composition — Hallmark, second pass

2026-11-13. Supersedes the earlier density-only correction. Read local hallmark/SKILL.md with redesign, layout-and-space, interaction/states, responsive and contract references. Existing FamilyDent handoff remains the brand authority; source export unchanged.

## Finding and decision

The earlier pass reduced whitespace but kept the same repeated form-card composition. Cabinets still opened as an equal-weight collection of creation forms. A work register should be the main surface; creation is an action, not the default page.

- Staff: study register first; actions New study/New patient/Add doctor open existing forms in native dialogs.
- Admin: compact team table with role/status/actions; clinic/account creation in dialogs.
- Doctor: existing scoped study search/list, simplified dividers and no enclosing rounded card.
- Shared: original fonts/palette/logo; fewer repeated headings, low-key test notice, rectangular controls and rows instead of large pills/panels. Logout remains visible/contrasting in topbar. No gradients, decorative icons, invented stats, theme rotation or new dependencies.

Only visual/presentation state changed. API, MFA, ownership scopes, database and actual form submission logic preserved. No deletion of production files. Added TaskDialog.tsx; amended Workspace.tsx/workspace.css and browser_check.py.

## Verification

Real browser passes password/TOTP QR, registration, study assignment, other-doctor isolation, revoke and admin denial of medical access. Modal opening, close button, Escape and return focus verified; default staff/admin page has no permanently open creation forms. Three roles across320/375/414/768/1024/1440/1920: no page overflow, logout enabled44px+, measured WCAG contrast>=4.5. Staff/admin dialogs also checked at all7 widths for overflow and viewport fit. Logout error retry + keyboard activation + API session invalidation checked. Synthetic screenshots only, no enrollment secret images saved. Build/typecheck/lint and repository immutable-handoff checks pass.

Subjective Hallmark self-review1–5: philosophy4, hierarchy5, execution4, specificity4, restraint5, variety4. Universal gates evaluated: contrast, tokens, keyboard, responsive affordances, no invented metrics/chrome/decoration. Marketing diversification gates do not apply to a shared view using an existing locked brand. Aesthetic acceptance remains with owner; no claim of69 automatic checks. Prior layout regression requiring adjacent forms was replaced by checks of the approved list-first behavior.

## Limits

No new clinical functionality, production deployment or auth reset. First pages of staff/team registers remain bounded as before. Closing an unfinished dialog discards its local unsaved form fields; already saved patient selection persists between registration steps. Native dialog supplies keyboard containment. Full v1 accessibility review is still ahead.

## OpenDesign component fidelity — 2026-11-13

Latest owner instruction asks to match the source elements more closely. [Component alignment](OPENDESIGN_COMPONENT_ALIGNMENT.md) supersedes the rectangular-control and borderless-panel choices above. Compact register-first workflow stays; source white bordered18px panels, pill actions,12px fields, gold navigation, serif form headings, outline icons and initial avatars are restored. Native dialogs remain, with a44px close icon. File picker now shows chosen filename with native keyboard/file-selection behavior; actual import bounds and security endpoints are unchanged.

Real browser flow passed MFA/upload/worker/review/OHIF/ZIP/revoke, external requests0.13-width role/dialog matrix and5-width file-picker focus/selection checks passed; screenshots visually compared with doctor/upload/admin source renderings using bundled local fonts. Original19 source files remain unchanged. No69-gate automatic claim; applicable contrast/keyboard/token/responsive/no-fake-content checks reviewed, shared-brand diversification intentionally disabled.
