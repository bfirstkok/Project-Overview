# AskMe Workboard — independent employee accounts

Public website: https://askme-kkn-workboard.spiritedmandrill.chatgpt.site

This web app uses its own employee accounts and a hosted Cloudflare D1 database. Ordinary employee login does not require Microsoft sign-in or Graph permissions. An optional Admin-only Excel read connection trial uses Microsoft Files.Read and is subject to company consent policies. The original Django application remains separate in the repository root.

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

25 automated checks cover the six-person roster, assignment permissions, Admin-only invite creation, sign-in/out, invite replay prevention, CSRF, password hashing, login throttling, task creation/idempotency, stale-write rejection, assignment/history consistency, progress/status independence, source date exceptions, and existing data transformations. Browser QA verifies account login, adding a task with multiple assignees, inline progress/status changes, activity history, account controls, and charts. Regression coverage includes 100% open work, explicit completion, cancellation, due-today boundaries, and matching table/card deadline labels. Responsive QA checks 390px phone and 1440px desktop layouts, mobile filtering, table edit mode, and dashboard closure links. The 214-row source copy is additionally round-tripped and compared field by field locally before production import.

Legacy `src/graph.js` and its transformation tests are retained for reference; the production entrypoint does not import it, and the deployed worker has no Microsoft client IDs or permissions.

## Optional Microsoft Excel read connection trial

Admin opens **ทีมของเรา → เชื่อม Excel ต้นฉบับ**. The trial requests only delegated `Files.Read` using the existing company SPA registration; it never requests a write scope or modifies the original workbook. The source sharing URL is a secret runtime `EXCEL_SHARE_URL`, never a public bundle or committed file. Microsoft access tokens stay in browser session storage and are passed transiently to the same-origin Admin-only read endpoint. They are not stored in D1 or logs.

The server uses GET-only Graph requests for the one configured file, strips the bearer before following a Microsoft download redirect, rejects untrusted hosts, and limits the response to 15 MB. It records only a read-check timestamp, byte count, SHA-256, and `syncEnabled:false`. This trial does not replace task data and does not enable automatic refresh until file access has actually succeeded. Microsoft may still require company administrator approval despite the read-only scope. Existing employee accounts and work remain usable if consent is denied.

Shared-file fallback: a separate explicit button can request delegated `Files.Read.All` for files shared with the signed-in user. This remains read-only but is broader than `Files.Read` and may require company approval. It is not requested by ordinary sign-in or the default read button. The fixed source URL and GET-only server restriction remain in effect. No automatic sync is enabled by this trial.
