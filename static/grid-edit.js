(() => {
  const root = document.querySelector('#task-register');
  if (!root) return;
  const message = document.querySelector('#sheet-message');
  const editable = () => root.classList.contains('register-editing');
  window.addEventListener('beforeunload', event => {if (root.dataset.bulkSaving) {event.preventDefault(); event.returnValue = '';}});
  root.addEventListener('keydown', event => {
    const cell = event.target.closest('[data-field]');
    if (!cell || !editable() || root.dataset.bulkSaving) return;
    if (event.key === 'Escape') {
      cell.value = cell.savedValue;
      cell.blur();
      return;
    }
    const enter = event.key === 'Enter' && cell.tagName !== 'TEXTAREA';
    const tab = event.key === 'Tab';
    const arrow = event.altKey && ['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(event.key);
    if (!enter && !tab && !arrow) return;
    event.preventDefault(); event.stopImmediatePropagation();
    if (!cell.checkValidity()) {cell.reportValidity(); return;}
    const rows = [...root.querySelectorAll('.sheet-row')];
    const row = cell.closest('tr'), td = cell.closest('td');
    let target;
    if (enter || (arrow && ['ArrowUp','ArrowDown'].includes(event.key))) {
      const direction = event.key === 'ArrowUp' || event.shiftKey ? -1 : 1;
      for (let i = rows.indexOf(row) + direction; i >= 0 && i < rows.length; i += direction) {
        target = rows[i].cells[td.cellIndex].querySelector('[data-field]:not(:disabled)');
        if (target) break;
      }
    } else {
      const cells = [...root.querySelectorAll('.sheet-row [data-field]')];
      const direction = event.shiftKey || event.key === 'ArrowLeft' ? -1 : 1;
      for (let i = cells.indexOf(cell) + direction; i >= 0 && i < cells.length; i += direction) {
        if (!cells[i].disabled) {target = cells[i]; break;}
      }
    }
    cell.dispatchEvent(new Event('change', {bubbles:true}));
    target?.focus();
    if (target?.type === 'text') target.select();
  }, true);

  // Parse Excel's quoted tab-separated clipboard, including newlines in notes.
  function parse(text) {
    const rows = [[]]; let value = '', quoted = false;
    for (let i = 0; i < text.length; i++) {
      const char = text[i];
      if (char === '"' && (quoted || !value)) {
        if (quoted && text[i+1] === '"') {value += '"'; i++;}
        else quoted = !quoted;
      } else if (!quoted && (char === '\t' || char === '\n' || char === '\r')) {
        rows.at(-1).push(value); value = '';
        if (char !== '\t') {if (char === '\r' && text[i+1] === '\n') i++; rows.push([]);}
      } else value += char;
    }
    if (quoted) throw new Error('เครื่องหมายคำพูดในข้อมูลไม่ครบ');
    rows.at(-1).push(value);
    if (rows.length > 1 && rows.at(-1).length === 1 && rows.at(-1)[0] === '') rows.pop();
    return rows;
  }
  function convert(control, raw) {
    let value = raw.trim();
    if (control.tagName === 'SELECT') {
      if (!value) return '';
      const matches = [...control.options].filter(option => option.textContent.trim().toLowerCase() === value.toLowerCase());
      if (matches.length !== 1) throw new Error('ไม่พบตัวเลือกที่ตรงกัน: ' + value);
      return matches[0].value;
    }
    if (control.type === 'date' && value) {
      let year, month, day;
      if (/^\d{4}-\d{2}-\d{2}$/.test(value)) [year,month,day] = value.split('-').map(Number);
      else if (/^\d{1,2}\/\d{1,2}\/\d{4}$/.test(value)) [day,month,year] = value.split('/').map(Number);
      else throw new Error('วันที่ต้องเป็น DD/MM/YYYY หรือ YYYY-MM-DD');
      if (year >= 2400) year -= 543;
      const check = new Date(Date.UTC(year,month-1,day));
      if (year < 1900 || year > 2100 || check.getUTCMonth() !== month-1 || check.getUTCDate() !== day) throw new Error('วันที่ไม่ถูกต้อง: ' + value);
      value = `${year}-${String(month).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
    }
    if (control.type === 'number') {
      value = value.replace(/%$/, '').trim();
      if (!/^\d+$/.test(value) || Number(value) > 100) throw new Error('ความคืบหน้าต้องเป็น 0–100');
    }
    if (control.maxLength > 0 && raw.length > control.maxLength) throw new Error('ข้อความยาวเกินกำหนด');
    return ['title','notes_to_colleague'].includes(control.dataset.field) ? raw : value;
  }
  root.addEventListener('paste', event => {
    const start = event.target.closest('[data-field]');
    const text = event.clipboardData?.getData('text/plain') || '';
    if (!start || !editable() || (!text.includes('\t') && (!text.includes('\n') || start.tagName === 'TEXTAREA'))) return;
    event.preventDefault();
    if (root.dataset.bulkSaving || root.querySelector('.sheet-row [data-field]:disabled')) {message.textContent = 'กรุณารอการบันทึกปัจจุบันก่อนวางข้อมูล'; return;}
    try {
      const matrix = parse(text), rows = [...root.querySelectorAll('.sheet-row')];
      const startRow = rows.indexOf(start.closest('tr')), startColumn = start.closest('td').cellIndex;
      if (matrix.length > 100 || startRow + matrix.length > rows.length) throw new Error('จำนวนแถวเกินหน้าปัจจุบัน กรุณาใช้ Import Excel สำหรับข้อมูลจำนวนมาก');
      const edits = [], preview = [];
      matrix.forEach((values, offset) => {
        const row = rows[startRow + offset], changes = {};
        values.forEach((raw, column) => {
          const control = row.cells[startColumn + column]?.querySelector('[data-field]');
          if (!control || control.disabled || row.dataset.conflict) throw new Error('ช่วงที่วางมีช่องที่ไม่มีสิทธิ์แก้ไขหรือเกินตาราง');
          const value = convert(control, raw);
          if (value === control.savedValue) return;
          changes[control.dataset.field] = value;
          preview.push([row.dataset.taskId, control.getAttribute('aria-label'), control.savedValue || '—', raw || '(ล้างค่า)']);
        });
        if (Object.keys(changes).length) edits.push({id:Number(row.dataset.taskId),version:Number(row.dataset.version),changes});
      });
      if (!edits.length) {message.textContent = 'ข้อมูลเหมือนเดิม ไม่มีการเปลี่ยนแปลง'; return;}
      const dialog = document.createElement('dialog'); dialog.className = 'grid-preview';
      const heading = document.createElement('h2'); heading.textContent = `ตรวจสอบก่อนบันทึก ${preview.length} ช่อง ใน ${edits.length} งาน`;
      const note = document.createElement('p'); note.textContent = 'ตรวจสอบสถานะและ % Complete แยกกัน ระบบจะบันทึกทั้งชุดเมื่อข้อมูลถูกต้อง';
      const wrap = document.createElement('div'); wrap.className = 'grid-preview-scroll';
      const table = document.createElement('table');
      const header = table.createTHead().insertRow();
      ['งาน #','ช่อง','ค่าเดิม','ค่าใหม่'].forEach(text => {const th = document.createElement('th'); th.textContent = text; header.append(th);});
      const body = table.createTBody();
      preview.forEach(values => {const tr = body.insertRow(); values.forEach(value => {tr.insertCell().textContent = value;});});
      wrap.append(table);
      const feedback = document.createElement('p'); feedback.setAttribute('role','status');
      const cancel = document.createElement('button'); cancel.className = 'btn btn-outline-secondary'; cancel.textContent = 'ยกเลิก';
      const save = document.createElement('button'); save.className = 'btn btn-primary'; save.textContent = 'ยืนยันบันทึกทั้งชุด';
      cancel.onclick = () => dialog.close();
      dialog.addEventListener('close', () => dialog.remove());
      dialog.addEventListener('cancel', event => {if (root.dataset.bulkSaving) event.preventDefault();});
      save.onclick = async () => {
        save.disabled = cancel.disabled = true; root.dataset.bulkSaving = 'true';
        feedback.textContent = 'กำลังบันทึก…';
        try {
          const response = await fetch('/tasks/grid/', {method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':document.querySelector('#sheet-csrf input').value},body:JSON.stringify({rows:edits})});
          const result = await response.json().catch(() => ({}));
          if (response.redirected || !response.ok) throw new Error(result.error || 'ไม่มีสิทธิ์หรือ session หมดอายุ');
          delete root.dataset.bulkSaving;
          window.location.reload();
        } catch (error) {
          feedback.textContent = error.message + ' · หากการเชื่อมต่อขัดข้อง กรุณาโหลดข้อมูลล่าสุดก่อนลองใหม่';
          save.disabled = false; cancel.disabled = false; delete root.dataset.bulkSaving;
        }
      };
      dialog.append(heading,note,wrap,feedback,cancel,save); document.body.append(dialog); dialog.showModal();
    } catch (error) {message.textContent = 'วางข้อมูลไม่ได้: ' + error.message;}
  });
})();
