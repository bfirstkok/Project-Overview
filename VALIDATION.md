# Validation — Excel Tracking + Microsoft 365 SSO

Updated 12 November 2026, Asia/Bangkok client context.

## Automated verification

| Check | Result |
|---|---|
| Django tests on PostgreSQL 17.11 | **80/80 passed**, 12.141 seconds |
| Concurrent edit test | Two real PostgreSQL connections/threads; one save, one conflict; version increments once |
| Database upgrade | Applied migrations 0002–0005 to the existing local database; retained tasks and assignments |
| `manage.py check` | No issues |
| `makemigrations --check --dry-run` | No changes detected |
| `pip check` | No broken requirements |
| `node --check static/app.js` | Passed |
| Python compileall | Passed |
| Production `check --deploy` | One expected warning: work.W001, Microsoft SSO credentials missing; no other warnings |
| `check_sso` | Correctly failed readiness: tenant ID, client ID and client secret are missing |

Tests use isolated test databases, not the local demo database. Coverage includes:

- Project/Task CRUD, versioned full forms, primary Sales/Engineer and additional assignments, personal tasks, role and team authorization.
- Inline status/progress/notes, forbidden reassignment, invalid values and wrong roles, stale form/inline/delete conflicts, and preservation of work when an old assignee is deactivated.
- Independent Status/Progress: setting progress=100 never changes status; selecting Complete never changes progress. Cancelled is excluded from pending/overdue metrics.
- All eleven table headers, search/filter/sort whitelist, pagination, real database Dashboard and primary-assignment workload.
- XLSX upload, column mapping, preview without writes, Buddhist dates, serial/percentage cells, user matching and ambiguity, manual mapping, membership, formulas, row limits, duplicates, no overwrite, repeated confirmation, preview revision, expired/private batches, error CSV, explicit partial import, and eleven-column export roundtrip.
- Comments/XSS escaping, authenticated file downloads, file validation, CSV/XLSX formula safety, CSRF, inactive users, POST logout and development login throttling.
- SSO policy rejects wrong tenant/issuer/domain/guest/inactive accounts; password login is disabled in production even when the development flag is true.
- Mocked OIDC discovery verifies the real allauth authorization redirect includes the company tenant, authorization-code flow, OAuth state, PKCE S256 and the correct callback path. Forged callback state cannot authenticate.

## Browser verification against real PostgreSQL

- Signed in using the clearly marked local Development demo login. Microsoft button correctly shows configuration is pending.
- Verified the main page contains the exact eleven-column task register and horizontal scrolling.
- Edited an existing synthetic UAT task through the table, including primary Sales and Engineer assignment.
- Typed progress changes and saved by Tab/Enter. Confirmed setting 100% left Status at In Progress. Only an explicit dropdown selection changed Status to Complete.
- Saved Notes to Colleague using Ctrl+Enter and confirmed version 8 and persisted values.
- Opened a second full-edit tab before an inline change. Submitting the stale form showed the conflict message and did not overwrite the current task.
- Uploaded a synthetic XLSX containing one valid row, one duplicate and one invalid-date row. Preview displayed **new=1, duplicate=1, error=1**. Explicitly selected import-valid-only and confirmed. Exactly one task was created; the invalid row was not created.
- Synthetic data is labeled as UAT, not company data inferred from an image.
- Checked a 1280px viewport: document 1265px, table viewport 947px, table content 2020px.
- Checked a 390px phone viewport: document 375px, table viewport 341px, table content 2020px. Horizontal overflow remains inside the table. Temporary viewport override was reset and QA tabs were closed.

The original user browser tabs were preserved. The localhost development server and project-scoped PostgreSQL remain available for local review.

## Limits and required external configuration

- **Real Microsoft 365 sign-in has not been tested** because the company's Entra tenant ID/client ID/client secret are not available. `SSO_SETUP.md` provides the exact steps and callback URI. Admin was provisioned from the user-specified corporate email locally with an unusable local password. The real email and credentials are not in source control.
- **Docker CLI/engine is not installed on this host.** Docker image build, Compose/Gunicorn on Linux and Caddy TLS issuance were not run. Their configuration is supplied for validation on the target host.
- The company's original Excel/image was not available in this update. Import and UI use the eleven-column structure specified in the user's requirements. Original-workbook acceptance remains to be checked when a real file is available.
- No production deployment, load test or backup recovery drill was performed. Deployment readiness is not inferred from unit tests.

Portable PostgreSQL is restricted to 127.0.0.1:15432 with SCRAM authentication under ignored `.local/`. A pre-upgrade dump is stored there. Secrets, staged import data, media, databases and runtime files are not committed.
