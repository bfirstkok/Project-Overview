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

## UI readability update

- Re-ran the existing PostgreSQL suite: **80/80 tests passed**, 12.784 seconds.
- Increased body/table text to 15px/14px, raised contrast, simplified visible filters and added actual filtered task summaries.
- Verified default read mode hides inline editors. Enabled editing, saved the synthetic UAT task progress at 99%, switched to cards and confirmed the card showed the saved 99%. Restored 100% through the same UI.
- Verified search returned two UAT tasks and clearing filters restored the list. Verified the sidebar collapse control expands working space.
- Verified phone width 390px: document 375px, automatic card layout, readable task names, assignments, dates and progress. Reset the viewport override afterward.
- Checked browser console: no JavaScript errors. Node syntax checks passed for both app.js and readable.js.

## Company Excel screenshot reference update

- The user supplied three screenshots of the original company To-do List. These are now layout references; no company records were transcribed, inferred or imported from the images. The original XLSX is still unavailable.
- Retained the eleven column names/order and increased emphasis on Project/Task/Notes, pale worksheet headers, visible grid lines and purple progress bars.
- Added compact rows (measured 39px height with 13px text), comfortable-row toggle, focus-table mode and bounded page-size choices 20/50/100. Focus mode moved the table viewport top to 196px in the desktop check.
- Full PostgreSQL regression suite: **81/81 passed**, 12.677 seconds, including the new page-size allowlist check.
- Browser verified compact/comfortable toggle, focus mode and selecting 100 rows. No JavaScript errors were recorded.


## Calendar, grid editing and source-workbook migration (2026-11-13)

- The original XLSX was supplied after the screenshot update. A private one-off transaction backed up application data, removed the 15 previous tasks and imported all 211 populated task rows as 202 projects. Blank numbered template rows were excluded. A repeated Project + Task pair was preserved as separate source rows.
- Independently compared every imported task's project, title, priority, status, dates, progress, Sales, Engineer/member set, notes, source No. and source row against the original workbook: all 211 matched. Preserved 193 Complete and 18 In Progress independently of progress values. One blank Engineer remains blank.
- At the user's explicit instruction, preserved the one source row whose End Date precedes Start Date. Retained original typed values and textual dates in private provenance; marked the date exception rather than correcting it. New invalid date edits remain rejected.
- Expanded the source ALL engineering group and multi-person cells into primary Engineer and additional members. No company email was fabricated. Imported roster entries have unusable passwords until Admin associates verified corporate email.
- Browser verified a day with 10 tasks: two grid previews, all ten in the daily agenda. At 390px, document width was 375px with no horizontal page overflow and the selected day's full task list below the month.
- Browser pasted two synthetic progress values (25 and 50) into separate rows, reviewed the old/new values and saved both. Versions advanced together; Status remained To Do. Tab moved from Task to Priority; Enter moved progress to the next row. Removed both QA rows afterward, restoring 211 company tasks. No browser JavaScript errors were recorded.
- PostgreSQL regression suite covers atomic grid saves, invalid-field rollback including audit history, stale-version rollback, per-field/team permissions, duplicate row rejection, calendar visibility and selected-day completeness, source No. filtering, legacy-date preservation, and additional Engineer metrics. Latest result is recorded after the final run below.
- Company XLSX, database, import scripts/reports, backups and screenshots remain outside Git. The code push does not publish company task records. Microsoft 365 live sign-in and Docker limitations above still apply.

Final PostgreSQL regression result: **91/91 passed**, 14.700 seconds. Django checks, migration drift check and Node syntax checks passed.


## Six-person roster and Intern assignment (2026-11-13)

- Backed up application data before updating the roster. The employee list contains six active people: three Sales, two Engineers and one Intern. Four old demo accounts were disabled and excluded from the employee roster; the local system administrator remains a separate non-employee account. Historical account references were retained.
- Preserved all 214 task IDs, versions, primary assignments, additional members, statuses, progress values and dates. Existing corporate administrator access was retained independently of the new Intern occupational role, without granting Django superuser status.
- Verified rendered task choices contain four Sales candidates and three Engineer candidates, with Intern in both; team and user pages each contain six employees. System accounts do not appear in assignment choices, employee pages or workload metrics.
- Full PostgreSQL suite: **96/96 passed**, 16.002 seconds. New checks cover both Intern assignment fields, assigned-task editing without automatic administrative access, Excel name matching, service-account exclusion, retained explicit administrative access and cross-team assignment restrictions. Django checks and migration drift check passed.


## Multiple Sales / Engineer assignees (2026-11-13)

- Added separate Sales and Engineer member relations, checkbox editors for full forms and a table dialog with explicit Save/Cancel. Intern is available in both team fields. Legacy primary FK callers remain supported.
- Backed up PostgreSQL before migration. Compared all 214 task IDs, titles, statuses, priorities, progress values, dates, notes, versions and effective assignee sets before/after migration: unchanged. Legacy additional team members moved into the corresponding team relation.
- Verified additional assignees have task access, edit permission, My Tasks, filtering, workload and team metrics. Assignment does not implicitly add a new person to every task in the project. Unauthorized role/team choices and non-manager assignment changes are rejected.
- PostgreSQL regression suite: **103/103 passed**, 26.115 seconds, including multiple-team access, retained assignments on note edits, stale versions, empty selections/full-form clearing, multi-person Excel roundtrip, atomic grid rollback and project isolation for newly assigned people.
- Browser selected and saved two Sales and three Engineers on a synthetic QA task. Reload retained all five selections; no JavaScript errors. Removed the QA task/project afterward and reverified the 214 original company tasks and all original effective assignments.
- Node syntax, Django system checks and migration drift checks passed. Private backups, screenshots, roster and company records remain outside source control.


## Readable dashboard charts (2026-11-13)

- Added four permission-scoped chart sections above operational task lists: task status, open workload per employee with overdue subset, open-task priority, and the next seven End Dates. Retained the existing canvas status chart and corrected small-segment gaps so a tiny nonzero segment cannot wrap around the ring.
- Workload counts each task once per employee across primary, group and additional assignments. Open tasks exclude Complete/Cancelled, independent of progress. Due-date charts zero-fill all seven local dates and exclude terminal tasks.
- Full PostgreSQL suite: **106/106 passed**, 23.933 seconds. Tests cover exact priority/daily counts including zeros, terminal-state exclusions, permission boundaries, duplicate-role deduplication and open-task drilldowns. A follow-up targeted drilldown check passed after adding the retained pending-filter input.
- Browser verified four rendered charts, a workload click opening exactly the displayed number of tasks, desktop light/dark status/workload charts, and mobile light priority/due charts. At 390px the document was 375px wide with seven day columns and no horizontal page overflow. Reset the temporary viewport and restored the original light theme. No browser JavaScript errors were recorded.
- Names in the compact operational task list now show all Sales/Engineer assignees instead of letter-only avatar placeholders. Source task data was not changed. Company screenshots stay outside Git.
- Repaired the ignored virtual environment's base-Python path after a bundled-runtime upgrade, restarted the stopped local PostgreSQL service, and ran verification with the restored local application. No credentials or runtime paths were added to application source.
