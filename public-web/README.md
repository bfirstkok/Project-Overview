# AskMe Workboard — independent employee accounts

Public website: https://askme-kkn-workboard.spiritedmandrill.chatgpt.site

This web app uses its own employee accounts and a hosted Cloudflare D1 database. Ordinary employee login does not require Microsoft sign-in or Graph permissions. Excel references use manually saved .xlsx copies and do not require Microsoft app consent. The previous online connection trial is disabled. The original Django application remains separate in the repository root.

## Using the app

1. The owner opens the one-time setup link supplied privately and sets a password (12–128 characters) for `khanathippakorn`, the first Admin. There is no default production password.
2. Admin opens **ทีมของเรา → บัญชีพนักงาน**, generates a one-time activation link, and gives it to the matching employee. Links expire in seven days; generating a replacement invalidates the previous link. The same flow resets a forgotten password.
3. Employees sign in with lowercase usernames: `panithan`, `araya`, `sabaipair`, `jakkarin`, `sayan`, `khanathippakorn`.
4. Work opens newest first. On smaller screens the readable card view opens by default; use **ตาราง Excel** to switch to the full 11-column spreadsheet. Read mode uses clear status badges; **แก้ไขในตาราง** enables inline Status/Priority/progress controls. Mobile secondary filters expand using **ตัวกรอง**. Search, filter, sort, change Status/Priority/progress inline, or open task details. **เพิ่มแถวงาน** creates a task. Both assignment groups support multiple people; the intern belongs to both groups.
5. Open **ภาพรวม** for status, priority, and employee workload charts. CSV export includes the current filtered result and opens in Excel.

All six employees can view team work. Assigned employees and task creators can edit their work; Admin can edit everything and manage activation links. The backend enforces permissions. Competing edits return HTTP 412 and keep the editor text for recovery. Progress never changes Status automatically. Open work at 100% is grouped as **รอปิดงาน**, excluded from overdue alerts and active workload, and retains its original Status until an authorized employee confirms **ยืนยันปิดงาน**. Complete and Cancelled tasks are never overdue. Due-today tasks are not overdue until the next Bangkok calendar day. Task details include actor, timestamp, and before/after activity.

## Data provenance

Initial migration uses the retained 214-row import snapshot from `To do list with progress tracker_AskMe KKN (1).xlsx`, SHA-256 `97e6c759cd6a728b0b8119ef0d459de996ae128254bd31c3556c068c56b22091`. It is a copy, not a live sync of SharePoint. No company records or import payloads are committed or embedded in public assets.

Original numbers and values are preserved, including No. 61's reverse date range (2026-04-29 to 2026-03-31). Source date strings such as 16/06/26 are normalized to ISO dates. Engineer ALL expands to Jakkarin, Sayan, and khanathippakorn; combined names become multiple assignees. Original raw source metadata is retained server-side. Editing other fields preserves the original reverse date range; new invalid date ranges are rejected.

Changes on this site do not modify or automatically synchronize the original Excel or Microsoft Lists. Keep exports as independent backups.

## Development

Requires Node 24+ (local tests use node:sqlite).

```sh
npm install
npm test
npm run build
node preview.mjs
```

Preview: http://127.0.0.1:5190, synthetic data only. Local disposable QA login: `khanathippakorn` / `local-qa-only-password`. It never connects to the production database. The preview database is in memory and resets when the process restarts.

Production build is a Worker ESM at `dist/server/index.js` with embedded public assets. `.openai/hosting.json` binds D1 as `DB`. Schema migrations under `drizzle/` are generated using `npm run db:generate`, remain schema-only, and are applied by Sites before deployment. Do not modify applied migrations. Local test and preview databases are separate from hosted data.

## First-time production bootstrap

Set a random secret runtime `SETUP_TOKEN` using Sites environment management, never in source or public config. Before initial activation, a protected `POST /api/setup/seed` imports a validated payload. Requests require same-origin `Origin` and `X-Setup-Token` headers. For batches, use `final:false` until the last batch and `expectedCount` on completion. Finalization records the filename/hash/count; `POST /api/setup/check` verifies them. The setup form reads `/#setup=<token>`, removes the fragment, and lets the owner choose a password. Setup endpoints become unavailable after activation. Never share setup links or commit seeds, sessions, credentials, or database copies.

Passwords use PBKDF2-SHA256 with individual random salts and 100,000 iterations. Sessions use random tokens stored as SHA-256 hashes with seven-day HttpOnly/Secure/SameSite=Strict cookies. Mutations require a same-origin Origin header. Login attempts are throttled. Public visitors receive no task data. CSP, frame restrictions, and no-store headers protect the login page and account responses.

## Validation

30 automated checks cover the six-person roster, assignment permissions, Admin-only invite creation, sign-in/out, invite replay prevention, CSRF, password hashing, login throttling, task creation/idempotency, stale-write rejection, assignment/history consistency, progress/status independence, source date exceptions, and existing data transformations. Browser QA verifies account login, adding a task with multiple assignees, inline progress/status changes, activity history, account controls, and charts. Regression coverage includes 100% open work, explicit completion, cancellation, due-today boundaries, and matching table/card deadline labels. Responsive QA checks 390px phone and 1440px desktop layouts, mobile filtering, table edit mode, and dashboard closure links. The 214-row source copy is additionally round-tripped and compared field by field locally before production import.

Legacy `src/graph.js` and its transformation tests are retained for reference; the production entrypoint does not import it, and the deployed worker has no Microsoft client IDs or permissions.


## Latest Excel reference copies

**Excel อ้างอิง** is a separate, read-only view of the latest saved workbook. The archive remains immutable. Admin can separately reconcile it into editable website tasks. Search, person/status/priority filters, latest-first sorting, card/table views, source dates, and progress work on the reference data. Task details cannot edit reference rows or display unrelated web-task history. All signed-in team members can view the reference and download its exact original bytes.

Admin chooses **บันทึกสำเนาใหม่**, selects an .xlsx file (up to 500 KB), and uses **ตรวจข้อมูลก่อนบันทึก**. The preview displays row counts, sample rows, validation errors, ignored empty rows, and preserved source-date warnings. **บันทึกเป็นสำเนาอ้างอิง** archives the validated copy after confirmation. Duplicate hashes do not create additional versions; a stale preview cannot replace a newer reference. Previous copies remain archived and immutable.

Source format: worksheet `To-Do List`, the existing 11 column titles, unique positive task numbers, valid dates and progress. Source strings are preserved; Buddhist year text is normalized for display. ALL expands to the approved Engineer roster. Original reversed date ranges are retained and flagged. No source workbook is modified.

The reference banner shows the filename, source modification timestamp from workbook metadata, import timestamp in Asia/Bangkok, and task count. It explicitly states that this is a saved copy, not a live Microsoft sync. The XLSX bytes and parsed rows are stored in the authenticated D1 archive table, never in public assets or Git. File access and upload permissions are checked by the backend. Request sizes and expanded ZIP sizes are bounded.

The first current reference is a fresh download on 17 November 2026 of `To do list with progress tracker_AskMe KKN.xlsx`: 215 tasks, workbook modification timestamp 2026-11-16T14:24:58Z, SHA-256 `f0b2f199084898e97bfe8508879b3596a22191b18eb335e7b61963fadf490dc7`. It is distinct from the initial 214-task web migration. Downloading this file used the signed-in OneDrive interface and did not change the original.

The previous `/api/excel/*` online connector returns HTTP 410. The frontend no longer initializes Microsoft authentication or requests additional permissions. Existing company app registrations and granted permissions are not changed.

## Reconcile Excel into web tasks

After saving a reference, Admin reviews the reconciliation preview, then chooses **สำรองและอัปเดตตารางงาน**. The same action is available as **อัปเดตตารางงานจากไฟล์นี้** on the reference page. Matching uses original source No., never an editable project title. Three-way comparison updates unchanged fields from Excel, adds missing source tasks, and preserves web edits. Divergent edits and unsupported rows are listed in the preview. No task is deleted and progress never sets status automatically. Original reversed source dates are preserved.

Each atomic D1 batch captures full task/assignment backup in reconciliation_runs, checks the preview snapshot, applies assignments and activity history, and rejects stale previews without partial writes. Admin can download a run backup at /api/reference/reconcile/backup/{runId}. An optional expiring one-use maintenance capability is scoped to an exact source SHA-256; it cannot log in, edit arbitrary tasks, or be reused. Runtime secrets are removed after the authorized migration.
