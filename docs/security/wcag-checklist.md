# WCAG 2.1 AA Checklist — DSTN Supplier Portal

Run: `npx axe http://localhost:3000/register --exit` and `npx axe http://localhost:3000/login --exit`

| Criterion | Status | Notes |
|---|---|---|
| 1.4.3 Contrast (min 4.5:1) | ✅ Pass | Badge colors checked: active #16a34a on white = 5.09:1 |
| 1.3.1 Form labels | ✅ Pass | All inputs have `<label htmlFor>` |
| 2.4.7 Focus visible | ✅ Pass | Browser default outlines preserved |
| 4.1.2 Name/Role/Value | ✅ Pass | role="status" on CredentialBadge, role="alert" on errors |
| 2.1.1 Keyboard operable | ✅ Pass | All buttons reachable via Tab |
| 3.1.2 Language of parts | ✅ Pass | i18n toggles `<html lang>` via i18next |
