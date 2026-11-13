# ProjectWork — Excel-Based Sales & Engineering Tracking

Django 5.2 LTS + Bootstrap 5 + PostgreSQL 17 + Docker Compose/Caddy ภาษาไทย ไม่มี AI หรือ frontend build pipeline

## หน้าหลัก

`/` และ `/tasks/` เป็น Spreadsheet-style To-do List ตาม 11 คอลัมน์:

**No. · Project Name · Task · Priority · Status · Start Date · End Date · % Complete · Sales · Engineer · Notes to Colleague**

- เปิดมาเป็นโหมดอ่านด้วยตัวอักษร 14–15px กด **เปิดแก้ไขในตาราง** เมื่อต้องการ Inline Editing ตามสิทธิ์ บันทึกเมื่อออกจากช่องหรือกด Enter (Notes ใช้ Ctrl+Enter / Command+Enter) แล้วกด **กลับโหมดอ่าน**
- เลือกตาราง Excel หรือการ์ดงานได้ มือถือเปิดการ์ดอัตโนมัติ มีปุ่มย่อ sidebar เพื่อเพิ่มพื้นที่ตาราง ชื่อ Project/Task ตรึงไว้เมื่อเลื่อนบนจอกว้าง และย้ายตัวกรองรองเข้าเมนูเพิ่มเติม
- Priority/Status Dropdown, Date Picker, Progress Bar และสีงานเกินกำหนด/เร่งด่วน/เสร็จ เลื่อนตารางแนวนอนได้
- กดหัวคอลัมน์เพื่อเรียงขึ้น/ลง ค้นหา Project/Task และกรอง Project, Sales, Engineer, ผู้รับผิดชอบรวม, Priority/Status มีตัวกรองเพิ่มเติมสำหรับ No., ชื่อ, Notes, ช่วงวันที่ และ % Complete
- No. แสดงเลขต้นฉบับสำหรับงานที่ย้ายจาก Excel หรือ task ID สำหรับงานใหม่ กดเลขหรือ “รายละเอียด” เพื่อเปิด full form, notes/comments, attachments และประวัติ
- Priority: **Low / Normal / High / Critical**
- Status: **To Do / In Progress / On Hold / Complete / Cancelled**
- **Status และ Progress 0–100 เป็นอิสระ ไม่มีการเปลี่ยนค่าใดอัตโนมัติจากอีกค่า** การเปลี่ยน dropdown เป็นการเลือกของผู้ใช้เอง
- Complete/Cancelled ไม่นับเป็นงานค้าง งานเกินกำหนด หรือ High Priority ที่ยังไม่เสร็จ
- แยก Project และ Task จริง แต่ละ Task มี Sales, Engineer, สมาชิกเพิ่มเติม และกำหนดการของตน งานไม่ผูก Project เป็นงานทั่วไป/ส่วนตัว
- Dashboard แยกที่ `/dashboard/`: Total/In Progress/Complete/Overdue/High, My Tasks, Tasks by Sales/Engineer, Workload by Employee และกิจกรรม

ได้รับภาพ To-do List ของบริษัทเป็น Reference แล้ว จึงปรับสัดส่วนคอลัมน์ Project/Task/Notes หัวตาราง เส้นแบ่งช่อง และแถบ Progress ให้ใกล้รูปแบบเดิม มีแถวกระชับ/แถวอ่านสบาย ปุ่มขยายพื้นที่ตาราง และเลือก 20/50/100 งานต่อหน้าได้ ได้รับไฟล์ .xlsx ต้นฉบับในภายหลังและย้ายข้อมูลเข้าเครื่องพัฒนาแล้ว โดยไม่เดาข้อมูลจากภาพ ข้อมูลบริษัทและข้อมูลสำรองเก็บเฉพาะเครื่อง ไม่รวมใน Git ส่วน seed/UAT ใช้สำหรับฐานข้อมูลทดลองแยกต่างหาก ไม่มี mock endpoint แทนฟังก์ชันจริง

## สิทธิ์และการทำงานพร้อมกัน

| บทบาท | ขอบเขต |
|---|---|
| Admin | ทั้งระบบ จัดการบัญชี/บทบาท/ทีม |
| Manager | งานและ Project ที่เกี่ยวข้องกับทีมตน ผ่านผู้สร้าง ผู้รับผิดชอบ เจ้าของ/สมาชิก Project รวมสิทธิ์ที่ได้รับโดยตรง |
| Sales / Engineer | งานที่สร้าง/รับผิดชอบ หรืออยู่ใน Project ที่ตนเป็นเจ้าของ/สมาชิก |

ผู้สร้างงานและ Manager/Admin ในขอบเขตสิทธิ์แก้ข้อมูลและ assignments ได้ Sales/Engineer/สมาชิกเพิ่มเติมที่รับผิดชอบแก้ Status, % Complete, Notes to Colleague และบันทึกการทำงานได้ ผู้อ่านงานแสดงความคิดเห็นได้ การมอบหมายใหม่ต้องใช้ผู้ใช้ active ในขอบเขตสิทธิ์และเป็นสมาชิก/เจ้าของ Project

การเอาคนออกจาก Project ไม่ถอด assignment ของ Task อัตโนมัติ ต้องถอดจาก Task ด้วยหากต้องการยกเลิกสิทธิ์ งานส่วนตัวไม่ใช่พื้นที่ลับจาก Manager ของทีม/Admin

Task/Project มี `version` ทุกการแก้ไขใช้ transaction + PostgreSQL row lock เทียบ version จากหน้าที่เปิดไว้ หากมีคนแก้ก่อนตอบ **409 Conflict** และไม่เขียนทับ เปิดเวอร์ชันล่าสุดเปรียบเทียบก่อนบันทึกใหม่ได้ การลบจากหน้าค้างก็ตรวจ version Activity เก็บ actor/time และค่าเดิม → ค่าใหม่ รวม notes และ assignments

## Excel Import / Export

เมนู **Import Excel** หรือ `/excel/import/`:

1. อัปโหลด `.xlsx` สูงสุด 5 MB / 2,000 แถวต่อครั้ง เลือก Worksheet และแถวหัวคอลัมน์ได้
2. Mapping คอลัมน์ของแต่ละช่อง ห้ามใช้คอลัมน์ซ้ำ Task จำเป็น ส่วนอื่นเว้นว่างได้
3. ตรวจ Sales/Engineer: จับคู่ username/ชื่อเต็มที่ตรงและไม่ซ้ำ หรือเลือกบัญชีจาก dropdown ตรวจ role/team/project membership ด้วย
4. Preview แสดงแถวใหม่/ซ้ำ/ผิด พร้อมเลขแถวและเหตุผล ดาวน์โหลดแถวผิดเป็น CSV ได้ ไม่มีการสร้างงานก่อนยืนยัน
5. ยืนยันนำเข้าใน transaction หากมีแถวผิดต้องแก้ก่อน หรือ **เลือกนำเข้าเฉพาะแถวที่ผ่านอย่างชัดเจน** ข้อมูลซ้ำถูกข้าม ไม่ update งานเดิม

กติกา:

- Duplicate คือ Project Name + Task หลัง normalize ตัวพิมพ์/ช่องว่าง ทั้งในไฟล์และงานเดิมที่มีสิทธิ์เห็น หากตั้งใจเป็นคนละงานให้ใช้ชื่อที่แยกชัดเจน
- No. ใน Export เป็นเลขต้นฉบับสำหรับงานที่ย้ายจาก Excel หรือ ID แอปสำหรับงานใหม่ ใช้ประกอบการตรวจซ้ำ ไม่เป็นคำสั่งเขียนทับ ID ใด
- รองรับ Excel dates/serials, `DD/MM/YYYY`, `YYYY-MM-DD` และปี พ.ศ. 4 หลัก แปลง พ.ศ. เป็น ค.ศ. ใน Preview ไม่เดาจากปี 2 หลัก
- % Complete ใช้จำนวนเต็ม 0–100 หรือ Excel percentage cell เช่น 0.75 ในรูปแบบ 75% ทศนิยมที่ไม่ใช่รูปแบบ % จะถูกปฏิเสธเพื่อป้องกันการตีความผิด
- ค่าว่าง Priority/Status/Progress ใช้ Normal / To Do / 0 ตามที่แจ้งหน้า Mapping ไม่เดาผู้รับผิดชอบหรือลูกค้า
- Project ว่างเป็น standalone; fill-down จากแถวก่อนหน้าต้องเลือกเอง กรณี Excel เดิมมี merged cells
- Project ใหม่ต้องสร้างก่อน หรือเลือกอนุญาตสร้างและเลือกประเภทให้ชัดเจน Customer เว้นว่าง ไม่สมมติข้อมูลบริษัท
- ตรวจชื่อ/วันที่/status/priority/progress/ขนาด Reject formulas ให้ Paste Values ก่อน ไม่ execute macro ใช้ defusedxml และจำกัดขนาด ZIP ที่ขยายแล้ว
- Preview มี revision และหมดอายุ 24 ชั่วโมง ตรวจซ้ำ/สิทธิ์ตอน confirm ป้องกันยืนยันซ้ำ ใช้ advisory transaction lock เพื่อ serialize imports ที่อาจซ้ำกัน
- Export Excel มี 11 คอลัมน์ พร้อม freeze panes/filter และ Instructions; Sales/Engineer ใช้ username เพื่อจับคู่กลับได้แน่นอน CSV ใช้ UTF-8 BOM และป้องกัน formula injection; XLSX เก็บข้อความเป็น string ไม่ประมวลผลสูตรจากผู้ใช้
- Export 11 คอลัมน์ไม่รวมสมาชิกเพิ่มเติม/attachments/comments ซึ่งยังอยู่ในแอปและฐานข้อมูล ไม่ใช่ full database backup

## Microsoft 365 SSO

ใช้งานจริงผ่าน Microsoft 365 `@askme.co.th` แบบ single tenant ใช้ OpenID Connect Authorization Code + PKCE และ state ตรวจ tenant/issuer และ stable object ID ไม่รับอีเมลที่กรอกเองเป็นหลักฐานล็อกอิน

**SSO จริงยังรอ Tenant ID / Client ID / Client Secret ของบริษัท** ปุ่ม Login บอกว่ารอการตั้งค่า ไม่เปิด password fallback บน production ดู [SSO_SETUP.md](SSO_SETUP.md) สำหรับวิธีหา App Registration, Redirect URI และรายการส่งต่อ IT

```powershell
python manage.py migrate
python manage.py bootstrap_sso_admin
python manage.py check_sso
```

`SSO_ADMIN_EMAIL` กำหนด Admin คนแรกใน environment คำสั่ง bootstrap ไม่สร้างรหัสผ่าน ต้อง Sign in ด้วย Microsoft จริง พนักงานใหม่ได้ role Engineer ในทีมเริ่มต้น Admin ปรับ role/team ได้ เพิ่มบัญชี corporate email ล่วงหน้าเพื่อกำหนด role ก่อน sign in ได้ อีเมลไม่ซ้ำแบบไม่สนตัวพิมพ์ บัญชีปิดใช้งานถูกปฏิเสธ

Local password login ใช้ได้เฉพาะ **DEBUG=true + ALLOW_LOCAL_LOGIN=true** สำหรับ localhost แม้ตั้ง flag=true ก็ถูกปิดเมื่อ DEBUG=false ไม่มี public signup ไม่เก็บ Microsoft access/refresh token ลงฐานข้อมูล

## รันในเครื่องนี้ (Windows)

```powershell
cd D:\Askme\ProjectWork\Project-Overview
.\scripts\start-local.ps1
```

เปิด http://127.0.0.1:8000 บัญชี demo และรหัสผ่านสุ่มอยู่ใน `.local/demo-login.txt` ซึ่งไม่ถูก commit ใช้กรอบ Development บนหน้า Login ระหว่างรอ Entra config หาก server ยังเปิดอยู่ไม่ต้องเปิดซ้ำ

สคริปต์เปิด PostgreSQL portable เฉพาะโปรเจกต์เมื่อพบ `.local/pgdata` (127.0.0.1:15432) แล้ว migrate/runserver ไม่มี Windows service หรือการแก้ PATH กด Ctrl+C เพื่อหยุดเว็บ แล้ว `scripts/stop-local-db.ps1` เพื่อหยุด DB สำหรับ background process ที่ส่งมอบใช้ `scripts/stop-local.ps1`

## ติดตั้งใหม่ / Docker

ต้องมี Docker Desktop/Engine หรือ Python 3.12+ และ PostgreSQL 17

```powershell
Copy-Item .env.example .env
# กรอก SECRET_KEY, POSTGRES_PASSWORD แบบสุ่มและค่าอื่นตาม environment
# สร้าง secret: python -c "import secrets; print(secrets.token_urlsafe(50))"
docker compose -f compose.yaml -f compose.local.yaml up --build -d
```

Local override เปิด HTTP/DEBUG ถ้าจะใช้ demo ให้ตั้ง ALLOW_LOCAL_LOGIN=true เฉพาะเครื่อง local และตั้ง DEMO_PASSWORD ผ่าน environment ก่อนสั่ง seed ไม่มี seed อัตโนมัติใน Docker

Production: ตั้ง domain/DNS, `DEBUG=false`, SECRET_KEY, DB password, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, SITE_ADDRESS และ Microsoft credentials ตาม `.env.example` ใช้ **`docker compose up --build -d` ไม่ใช้ compose.local.yaml** Caddy จัด HTTPS, web ใช้ Gunicorn/WhiteNoise, db/media อยู่ใน named volumes ไม่ publish db/web ports

ตั้ง SSO_ADMIN_EMAIL จริง แล้ว `docker compose exec web python manage.py bootstrap_sso_admin` และทดสอบ Sign in จริงตาม [คู่มือ SSO](SSO_SETUP.md)

Native Python:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
# สร้าง .env: DEBUG=true, DB_ENGINE=postgres, POSTGRES_HOST/PORT/DB/USER/PASSWORD ของเครื่อง
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

ใช้ PostgreSQL สำหรับ concurrent editing จริง SQLite เป็นโหมดทดลอง ไม่รับประกัน row locking บน SQLite

ข้อมูลตัวอย่าง: ตั้ง `DEMO_PASSWORD` ผ่าน environment แล้ว `python manage.py seed_demo` สร้างแถวจริงแต่ระบุเป็นข้อมูลทดลอง ห้าม seed production

## Tests และตรวจ deploy

```powershell
.\.venv\Scripts\python.exe manage.py test --noinput
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py check --deploy
.\.venv\Scripts\python.exe manage.py check_sso
```

ผลที่รันจริงดู [VALIDATION.md](VALIDATION.md) Tests ใช้ test database แยก dev/CI database user ต้องมี CREATEDB ไม่รัน tests บน production `check --deploy` เตือน work.W001 หาก production ยังไม่มี SSO config ส่วน `check_sso` บอกว่าค่าครบเท่านั้น ไม่แทนการล็อกอิน Microsoft จริง

## Backup และขอบเขต MVP

สำรอง PostgreSQL กับ media volume ควบคู่กัน เก็บ `.env` ผ่าน secret store ตัวอย่าง backup ที่ไม่ให้ PowerShell เปลี่ยน encoding ของ binary:

```powershell
docker compose exec db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/projectwork.dump'
docker compose cp db:/tmp/projectwork.dump ./projectwork.dump
```

ทดสอบ restore ไปยังฐานข้อมูลว่างก่อนใช้จริง ไม่ใช้ Excel Export แทน DB backup ก่อนอัปเกรด local เก็บ `.local/pre-excel-upgrade.dump` ไว้แล้ว Upgrade แปลง Medium → Normal และแยกผู้รับผิดชอบเดิมตาม role โดยคงข้อมูลเดิมไว้

ยังไม่มี Notifications, Kanban drag-and-drop, realtime, recurring calendar, soft-delete/undelete, antivirus scanning หรือ multi-tenant isolation ไฟล์แนบจำกัด 5 MB/allowlist ตรวจสิทธิ์ดาวน์โหลด ไม่มี public /media/ Audit เป็น application log ไม่ใช่ tamper-proof log; ORM/DB edits โดยตรงอยู่นอก audit ของแอป ไฟล์เก่าที่ parent ถูกลบอาจคงอยู่ ต้องกำหนด retention/cleanup

Google Fonts เป็น optional มี system fallback; Bootstrap/CSS/JS อยู่ใน repository

Docker build/Compose/Caddy และ Microsoft SSO จริงยังต้องทดสอบบน host/tenant เป้าหมาย เครื่องพัฒนาไม่มี Docker และยังไม่มีค่าการเชื่อมต่อ Entra ของบริษัท


## ปฏิทินและการแก้ไขแบบ Excel

ปฏิทินแสดงตาม End Date เลือกวันเพื่ออ่านรายการงานเต็มพร้อมผู้รับผิดชอบและความคืบหน้า ด้านข้างบนคอมพิวเตอร์หรือด้านล่างบนมือถือ มีปุ่มเดือนก่อน/ถัดไป วันนี้ และเลือกเดือน ช่องวันแสดงตัวอย่างไม่เกินสองงานพร้อมจำนวนงานที่เหลือ งานไม่มี End Date แจ้งจำนวนแยกไว้

ในตาราง กด **เปิดแก้ไขในตาราง** หรือดับเบิลคลิกช่องที่แก้ไขได้ ใช้ Tab / Shift+Tab เลื่อนช่อง, Enter / Shift+Enter เลื่อนแถว, Alt+ลูกศรเลื่อนตำแหน่ง และ Escape คืนค่าที่ยังไม่บันทึก Notes ใช้ Ctrl+Enter บันทึก

วางช่วงข้อมูลจาก Excel ที่ช่องเริ่มต้นได้ ระบบแสดงค่าเดิม/ค่าใหม่ก่อนยืนยัน รองรับแถวที่แสดงอยู่ไม่เกิน 100 งานต่อครั้ง โดยต้องมีสิทธิ์แก้ไขทุกช่อง ชื่อ Dropdown ต้องตรงตัวเลือก วันที่รองรับ DD/MM/YYYY, YYYY-MM-DD และปี พ.ศ. บันทึกทั้งช่วงใน transaction เดียว หากข้อมูลผิดหรือ version ชนกันจะไม่บันทึกทั้งชุด Status กับ Progress แยกกันเสมอ การวางข้ามหน้าให้ใช้ Excel Import

งานที่ย้ายจากไฟล์จริงเก็บเลข No., แถว, ชีต, ชื่อไฟล์, SHA256 และค่าต้นฉบับไว้ใน source_data การย้ายครั้งนี้เก็บแถวชื่อซ้ำทุกแถวและวันที่ตามต้นฉบับตามคำสั่งผู้ใช้ มีข้อยกเว้นวันที่ที่ระบุชัดด้วย source_date_exception พร้อมคำเตือนในรายละเอียดงาน ข้อยกเว้นอนุญาตให้เก็บวันที่เดิมและแก้ช่องอื่นได้ แต่การเปลี่ยนเป็นคู่วันที่ผิดลำดับใหม่ยังถูกปฏิเสธ Import ปกติยังตรวจวันที่และข้อมูลซ้ำตามเดิม

รายชื่อจาก Excel ที่ยังไม่มีอีเมลเก็บด้วยรหัสผ่านที่ใช้ไม่ได้และไม่เดาอีเมลบริษัท Admin ต้องผูกอีเมลจริงกับบัญชีเดิมก่อนพนักงานเข้า Microsoft SSO เพื่อให้งานยังอยู่กับบุคคลเดิม งานที่มี Engineer หลายคนใช้ Engineer หลักและสมาชิกเพิ่มเติม โดยตัวกรอง Engineer และ Dashboard นับสมาชิกเพิ่มเติมด้วย


## พนักงานและ Intern

Role `Intern` มอบหมายได้ทั้ง Sales และ Engineer ผ่านฟอร์ม, ตาราง Inline และ Excel Mapping โดยยังตรวจสิทธิ์ผู้แก้ไขและสมาชิกโปรเจกต์จาก Backend เช่นเดิม Intern ทั่วไปไม่มีสิทธิ์ Manager/Admin การคงสิทธิ์ผู้ดูแลเดิมใช้ `has_admin_access` แยกจากตำแหน่งงาน ไม่ได้ให้สิทธิ์ผู้ดูแลกับ Intern ทุกคน

บัญชีระบบที่ตั้ง `is_service_account` ไม่แสดงในรายชื่อพนักงาน ตัวเลือกมอบหมายงาน ตัวกรองบุคคล หรือ Workload เก็บบัญชีเหล่านี้แยกเพื่อรักษาประวัติและการเข้าดูแลระบบ พนักงานปัจจุบันจัดเป็น Sales 3, Engineer 2 และ Intern 1 คน ข้อมูลบัญชีจริงเก็บเฉพาะฐานข้อมูลในเครื่อง


## มอบหมายหลายคนใน Sales / Engineer

เปิดโหมดแก้ไขในตาราง คลิกชื่อในช่อง Sales หรือ Engineer แล้วติ๊กเลือกหลายคนและกดบันทึก ไม่ต้องกด Ctrl ค้าง ฟอร์มรายละเอียดใช้ช่องติ๊กแบบเดียวกัน Intern เลือกได้ทั้งสองช่อง รายชื่อทั้งหมดแสดงในตาราง การ์ด ปฏิทินและ Excel Export

เก็บรายชื่อทีมแยกใน `sales_members` และ `engineer_members` ส่วน FK เดิมเป็นผู้รับผิดชอบหลักเพื่อรองรับข้อมูลเก่า Migration ย้ายสมาชิกเพิ่มเติมเดิมตามทีมเข้าช่องที่ตรงกัน ผู้รับผิดชอบทุกคนดูและอัปเดตงานตามสิทธิ์ได้ Filter, My Tasks และ Dashboard นับสมาชิกทุกคนโดยไม่นับงานซ้ำ

การเลือกหลายคนตรวจขอบเขตผู้ใช้ บทบาท และสิทธิ์แก้ไขจาก Backend ผู้ที่ได้รับมอบหมายใหม่เข้าถึงงานนั้นได้โดยไม่ต้องเพิ่มเป็นสมาชิกของทุกงานใน Project การเพิ่มสมาชิกทั่วไปยังตรวจสมาชิกโปรเจกต์ตามเดิม และการใช้ API แบบผู้รับผิดชอบหลักเดิมยังรักษากติกาเดิม ทุกครั้งตรวจ version และบันทึกประวัติ การแก้ช่องอื่นไม่ล้างรายชื่อหลายคน

Excel Import/Export ใช้ 11 คอลัมน์เดิม แต่ Sales/Engineer มีหลายชื่อได้ คั่นด้วยจุลภาค, `&`, `/` หรือขึ้นบรรทัดใหม่ ชื่อแต่ละคนมีการจับคู่และตรวจสิทธิ์แยกกัน ค่า ALL แสดงจำนวนตามขอบเขตสิทธิ์ใน Preview ก่อนยืนยัน
