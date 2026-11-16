# AskMe Workboard — static web + Microsoft Lists

หน้าเว็บใช้งานผ่านอินเทอร์เน็ตได้ โดยข้อมูลจริงยังเก็บใน Microsoft Lists ของบริษัท ไม่ฝังรายการงานหรือบัญชีลับในไฟล์เว็บ โหมดทดลองใช้ข้อมูลสมมติในหน่วยความจำและไม่ติดต่อ Microsoft

## ความสามารถ

- ตาราง 11 คอลัมน์ ค้นหา กรองคน/สถานะ/Priority และเรียงคอลัมน์ เริ่มต้นงานใหม่ก่อน
- เพิ่มงานด้วยฟอร์ม เลือก Sales และ Engineer ได้หลายคน Intern อยู่ได้ทั้งสองทีม
- เปลี่ยน Status/Priority และ % ในตาราง เปอร์เซ็นต์บันทึกเมื่อออกจากช่องหรือกด Enter
- % ไม่เปลี่ยน Status อัตโนมัติ มีการยืนยันเมื่อเปลี่ยน Status ในตาราง
- ภาพรวมสถานะ Priority และภาระงานต่อคน คลิกกราฟเพื่อกรองงาน
- ส่งออก CSV แบบ UTF-8 สำหรับ Excel พร้อมป้องกันสูตรจากข้อความที่นำออก
- PATCH เฉพาะข้อมูลที่แก้ พร้อม `If-Match` จาก eTag เมื่อมีการแก้พร้อมกันจะตอบ 412 และเก็บฟอร์มไว้ให้ตรวจสอบ
- เก็บวันที่ต้นฉบับที่สิ้นสุดก่อนเริ่มไว้หากไม่ได้แก้วัน ตรวจวันที่ใหม่ตามปกติ

## เริ่มบนเครื่อง

```sh
npm ci
npm test
npm run build
python -m http.server 8765 --bind 127.0.0.1 --directory dist
```

## เปิดข้อมูลจริง — ต้องทำให้ครบก่อนใช้งานบริษัท

1. ลงทะเบียน Microsoft Entra app แบบ Single tenant, platform **Single-page application (SPA)**
2. Redirect URI ต้องตรงกับ URL รากที่ใช้จริง รวม `/` ท้าย URL สำหรับเครื่องทดสอบเพิ่ม `http://localhost:8765/`
3. ตั้ง Graph **delegated** permission `Sites.ReadWrite.All` และให้ผู้ดูแลบริษัทพิจารณา consent ตามนโยบาย สิทธิ์นี้ให้แอปทำงานในนามผู้ใช้ได้กว้างกว่ารายการนี้ จึงควรให้ IT พิจารณาทางเลือก `Lists.SelectedOperations.Selected` และ explicit list grant หากบริษัทต้องการจำกัดแอปเฉพาะ List นี้ ก่อนเปลี่ยน scope ต้องทดสอบ Graph endpoint ทุกจุดกับสิทธิ์ที่เลือก
4. ใส่ Application (client) ID ใน `public/config.json` ค่า Client ID/Tenant ID เป็น public identifiers ไม่มี Client Secret สำหรับ SPA
5. ให้บัญชีพนักงานจริงเข้าถึง List ผ่าน SharePoint permissions ไม่มีการเดาอีเมลจากชื่อ ปัจจุบันรายชื่อทีมใน UI เป็น Choice ไม่ใช่การให้สิทธิ์
6. ทดสอบล็อกอิน อ่าน เพิ่ม และ PATCH กับบัญชีจริง รวมการปฏิเสธบัญชีที่ไม่มีสิทธิ์และกรณี eTag เก่า
7. ตั้ง List versioning ให้เก็บประวัติแก้ไข ตรวจข้อกำหนดการเก็บข้อมูลของบริษัท

Microsoft Graph เป็นผู้ตรวจสิทธิ์จริงบนเซิร์ฟเวอร์ การตรวจ domain ในเว็บมีไว้แจ้งผู้ใช้ ไม่ได้ใช้แทนสิทธิ์ SharePoint **ไม่มีการจำกัดสิทธิ์แก้เฉพาะงานที่มอบหมายด้วยชื่อ Choice** หากต้องการนโยบายนี้ต้องตั้ง item permissions/กลุ่มหรือเพิ่ม backend ก่อนเปิดให้ทีมใช้

## แหล่งข้อมูล

เชื่อม List ใหม่ที่สร้างจากสำเนา Excel ของบริษัท ไม่มีการแก้ไฟล์ Excel ต้นฉบับ รายชื่อ Engineer แบบข้อความหลายชื่อและ `ALL` ถูกอ่านแยกเป็นรายชื่อโดย `people()` เพื่อรองรับข้อมูลที่ยังไม่ได้จัดรูปแบบใน List

ค่า start/end อ่านวันที่ ISO จาก Graph ต้องตรวจเทียบกับวันใน Lists และ timezone ของ SharePoint เมื่อเปิดเชื่อมจริงก่อนรับรองการย้ายข้อมูล ห้ามสรุปว่าทดสอบข้อมูลจริงผ่านในช่วงที่ยังไม่มี Client ID/consent

## เผยแพร่ฟรี

เป็น static files จึงใช้ Cloudflare Pages Free ได้: เชื่อม GitHub, root `public-web`, build `npm ci && npm run build`, output `dist` โดยขึ้นกับโควตาและเงื่อนไขแพลตฟอร์ม ไม่มี PostgreSQL หรือเครื่องเซิร์ฟเวอร์ที่ต้องเปิดค้าง

Sites hosting identity อยู่ใน `.openai/hosting.json` เผยแพร่ผ่าน Sites helper ตาม workflow ประจำแพลตฟอร์ม ไฟล์ `_headers` ใช้ตั้ง headers บน Cloudflare Pages ผู้ดูแลควรตรวจ response headers ของโฮสต์ที่ใช้จริงด้วย

## ขอบเขตการทดสอบ

`npm test` ตรวจ mapping, หลายผู้รับผิดชอบ, วันที่ต้นฉบับ, patch เฉพาะช่องที่แก้, 412, 403 และ pagination ด้วย mocked Graph responses การทดสอบนี้ไม่ใช่หลักฐานว่าบัญชีบริษัทอนุมัติสิทธิ์แล้ว ทดสอบ UI ผ่านเบราว์เซอร์ด้วยข้อมูลสมมติแยกจาก List จริง

อ้างอิง: [MSAL SPA](https://learn.microsoft.com/en-us/entra/msal/javascript/browser/about-msal-browser), [Graph conditional updates](https://learn.microsoft.com/en-us/graph/api/listitem-update), [Selected permissions](https://learn.microsoft.com/en-us/graph/permissions-selected-overview)
