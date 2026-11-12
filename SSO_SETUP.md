# Microsoft 365 SSO — @askme.co.th

ระบบเชื่อม Microsoft Entra ID ด้วย OpenID Connect ผ่าน django-allauth ตรวจ tenant/issuer, audience/expiry ผ่าน provider, `oid` เป็นตัวระบุบัญชีถาวรใน tenant และตรวจ User Principal Name ว่าลงท้าย `@askme.co.th` โดยตรง ปฏิเสธโดเมนอื่น tenant อื่น และ guest identity ที่ตรวจพบจาก claims

**สถานะการส่งมอบ:** มีโค้ดและ tests สำหรับ SSO แล้ว แต่ยังไม่มี Tenant ID / Client ID / Client Secret ของบริษัท จึงยังไม่ได้ทดสอบเข้าสู่ระบบ Microsoft จริง ปุ่มบนหน้า Login จะแสดงว่ารอการตั้งค่า ไม่มีการจำลองว่าล็อกอินสำเร็จ

## ถ้าไม่ทราบว่าบริษัทมี App Registration แล้วหรือยัง

ให้ผู้ดูแล Microsoft 365 หรือผู้มีสิทธิ์ดู App registrations ของบริษัทเปิด [Microsoft Entra admin center](https://entra.microsoft.com/) ตรวจ Directory ที่เป็นของบริษัท จากนั้นไป Entra ID → App registrations → All applications ค้นหาชื่อ ProjectWork / Project-Overview หรือแอปภายในที่ทีม IT เตรียมไว้

หากเห็นเฉพาะ Enterprise applications อย่าสับสนกับ App registrations: ต้องมี Application (client) ID, Directory (tenant) ID และสิทธิ์ตั้ง Redirect URI/credentials ของแอปนั้น หากไม่มีสิทธิ์ให้ผู้ดูแล Microsoft 365 ช่วยตรวจ แทนการเดา ID หรือใช้ App Registration ของระบบอื่น

ข้อความส่งต่อให้ IT ได้:

> ต้องการเชื่อม ProjectWork กับ Microsoft 365 ของบริษัทแบบ Single tenant สำหรับผู้ใช้ @askme.co.th กรุณาตรวจ App Registration ที่มีอยู่ หรือสร้างแอปเฉพาะระบบนี้ กำหนดแพลตฟอร์ม Web และ Redirect URI ตามด้านล่าง ต้องใช้ Directory (tenant) ID, Application (client) ID และ Client Secret Value โดยใส่ Secret ใน .env ของเซิร์ฟเวอร์โดยตรง ไม่ส่ง Secret ในแชตหรือ GitHub ระบบใช้เพียง openid/profile/email ไม่ต้องใช้สิทธิ์อ่านอีเมลหรืออ่านทั้ง Directory

## ตั้ง App Registration

1. เลือกแอปเฉพาะ ProjectWork หรือ New registration เมื่อ IT ยืนยันว่าไม่มีแอปเดิม ตั้ง Supported account types เป็น **Accounts in this organizational directory only (Single tenant)**
2. ใน Overview จด **Directory (tenant) ID** และ **Application (client) ID** ไม่ใช่ Object ID ของ App Registration และไม่ใช้ `common` / `organizations` แทน tenant UUID
3. Authentication → Add a platform → **Web** ตั้ง Redirect URI สำหรับ local:

   ```text
   http://localhost:8000/accounts/oidc/microsoft/login/callback/
   ```

   สำหรับ production ใช้ domain HTTPS จริง:

   ```text
   https://<domain-ของระบบ>/accounts/oidc/microsoft/login/callback/
   ```

   ใช้ origin เดียวกันตอนเปิดเว็บเพื่อ Sign in; ถ้าลงทะเบียน localhost ให้เปิด `http://localhost:8000` ไม่สลับกับ `127.0.0.1` ไม่ต้องเปิด implicit grant สำหรับ flow นี้
4. Certificates & secrets → สร้าง Client Secret ตามนโยบายบริษัท ใช้ **Value** ไม่ใช่ Secret ID บันทึกใน secret store / `.env` ของเครื่องปลายทาง ตั้งวันหมดอายุและแผนหมุนเวียน
5. ใช้ scopes `openid profile email` ที่ระบบขอโดยอัตโนมัติ และให้ผู้ดูแลอนุมัติ consent ตามนโยบาย tenant ไม่ต้องเพิ่ม Mail.Read, Directory.Read.All หรือ permission ที่ไม่เกี่ยวข้อง
6. ตรวจว่า ID token มี `oid`, `tid`, `preferred_username` และ UPN ของผู้ใช้เป็น `@askme.co.th` การอนุญาตใช้ principal ของบริษัท ไม่ใช้เพียงชื่อแสดงผลหรืออีเมลที่กรอกเอง แนะนำเพิ่ม optional claim `acct` ใน ID token เพื่อแยก guest ให้ชัดเจน ระบบยังตรวจ issuer/tenant/identity provider และโดเมน UPN ด้วย
7. กำหนด Users/Groups ที่ใช้แอปได้ใน Entra ตามนโยบายบริษัท และใช้ Conditional Access/MFA ของบริษัทตามปกติ

อ้างอิง: [Microsoft: register an application](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app), [Redirect URI](https://learn.microsoft.com/en-us/entra/identity-platform/how-to-add-redirect-uri), [ID token claims](https://learn.microsoft.com/en-us/entra/identity-platform/id-token-claims-reference), [allauth OpenID Connect](https://docs.allauth.org/en/latest/socialaccount/providers/openid_connect.html)

## ตั้งค่าใน ProjectWork

ใส่ค่าจริงใน `.env` (ไม่ใส่วงเล็บ placeholder):

```dotenv
MICROSOFT_TENANT_ID=<Directory tenant UUID>
MICROSOFT_CLIENT_ID=<Application client ID>
MICROSOFT_CLIENT_SECRET=<Client Secret Value>
SSO_ADMIN_EMAIL=<อีเมลจริงของ Admin @askme.co.th>
ALLOW_LOCAL_LOGIN=false
```

สำหรับ production ตั้ง `DEBUG=false`, `SITE_ADDRESS=<domain>`, ALLOWED_HOSTS และ CSRF_TRUSTED_ORIGINS ให้ตรง HTTPS domain ด้วย

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py bootstrap_sso_admin
.\.venv\Scripts\python.exe manage.py check_sso
```

Docker ใช้ `docker compose exec web python manage.py ...` หลังแก้ `.env` ให้ recreate web container ด้วย `docker compose up -d --force-recreate web` ก่อนรันคำสั่ง เพื่อโหลด environment ใหม่

`bootstrap_sso_admin` เตรียมบัญชี Admin ด้วยอีเมลที่ระบุและตั้งรหัสผ่านเป็น unusable ไม่สร้างรหัสผ่านในระบบแทน Microsoft ต้อง Sign in ด้วยบัญชีบริษัทจริงจึงจะเข้าได้ แอดมินคนแรกที่ผู้ใช้ระบุถูกเตรียมไว้เฉพาะฐานข้อมูล local และ `.env` แล้ว อีเมลจริงไม่ถูกใส่ใน source code หรือ Git

พนักงานใหม่ที่ผ่าน SSO ได้บทบาท Engineer ในทีม Sales & Engineering เป็นค่าเริ่มต้น Admin เปลี่ยนเป็น Sales/Manager และจัดทีมได้ในหน้าผู้ใช้งาน หาก Admin เพิ่มบัญชีไว้ก่อน ให้กรอก corporate email ให้ตรง principal ระบบจะเชื่อมบัญชีนั้นหลังตรวจ identity สำเร็จ อีเมลไม่ซ้ำแบบไม่สนตัวพิมพ์เล็กใหญ่ บัญชีที่ปิดใช้งานจะถูกปฏิเสธ

## ตรวจการใช้งานจริงหลังตั้งค่า

- `check_sso` บอกเพียงว่าค่าครบ ไม่ใช่หลักฐานว่า consent/secret/domain ถูกต้อง ต้องทดสอบ Sign in จริง
- Sign in ด้วย Admin ที่กำหนด → เห็นเมนูจัดการผู้ใช้ → Sign out → พนักงาน Sales/Engineer Sign in → เห็นงานตามสิทธิ์
- ทดสอบปฏิเสธบัญชีต่าง tenant / ต่างโดเมน และบัญชีที่ปิดใช้งาน
- ถ้า Microsoft แจ้ง redirect mismatch ให้เทียบ URI รวม scheme, hostname, path และ trailing slash ให้ตรงทุกตัว
- ถ้า secret หมดอายุให้ IT สร้าง/หมุนเวียน Secret ตามนโยบาย แล้วอัปเดต `.env` และ restart web
- เมื่อต้องปิดสิทธิ์พนักงาน ให้ปิดผู้ใช้ในแอปด้วยเพื่อหยุด session ของแอปทันที ไม่อาศัยเฉพาะการปิดบัญชีใน Entra

## บัญชีทดลอง

ระบบอนุญาต password login เฉพาะเมื่อ **DEBUG=true และ ALLOW_LOCAL_LOGIN=true พร้อมกัน** เพื่อทดสอบ localhost เท่านั้น หน้า Login จะแยกไว้ในกรอบ Development ไม่ใช่ SSO การตั้ง ALLOW_LOCAL_LOGIN=true ไม่มีผลเมื่อ DEBUG=false ไม่เปิด public self-signup และไม่เก็บ access/refresh tokens ของ Microsoft ลงฐานข้อมูล
