(() => {
  const root = document.querySelector('#task-register');
  document.querySelector('#sidebar-toggle')?.addEventListener('click', event => {
    const collapsed = document.body.classList.toggle('sidebar-collapsed');
    event.currentTarget.setAttribute('aria-expanded', String(!collapsed));
    event.currentTarget.title = collapsed ? 'แสดงเมนูด้านข้าง' : 'ซ่อนเมนูเพื่อขยายพื้นที่ทำงาน';
  });
  if (!root) return;
  const editButton = document.querySelector('#editing-toggle');
  const tableButton = document.querySelector('#layout-table');
  const cardsButton = document.querySelector('#layout-cards');
  const help = document.querySelector('#register-help');
  const focusButton = document.querySelector('#focus-table');
  let sidebarBeforeFocus = false;
  function focusTable(on) {
    if (on) sidebarBeforeFocus = document.body.classList.contains('sidebar-collapsed');
    document.body.classList.toggle('register-focus', on);
    document.body.classList.toggle('sidebar-collapsed', on || sidebarBeforeFocus);
    focusButton?.setAttribute('aria-pressed', String(on));
    if (focusButton) focusButton.textContent = on ? '⛶ กลับหน้าปกติ' : '⛶ ขยายตาราง';
  }
  focusButton?.addEventListener('click', () => focusTable(!document.body.classList.contains('register-focus')));
  const densityButton = document.querySelector('#density-toggle');
  root.classList.add('register-compact');
  densityButton?.addEventListener('click', () => {
    const compact = root.classList.toggle('register-compact');
    densityButton.setAttribute('aria-pressed', String(compact));
    densityButton.textContent = compact ? 'แถวกระชับ' : 'แถวอ่านสบาย';
  });
  function cellText(control) {
    const raw = control.savedValue ?? ProjectWorkCells.value(control);
    let value = raw;
    if (control.multiple) {const ids = JSON.parse(raw || '[]'); value = [...control.options].filter(option => ids.includes(option.value)).map(option => option.textContent).join(', ');}
    else if (control.tagName === 'SELECT') value = [...control.options].find(option => option.value === raw)?.textContent || '';
    if (control.type === 'date' && raw) {
      const [year, month, day] = raw.split('-');
      value = `${day}/${month}/${year}`;
    }
    return value || '—';
  }
  function refreshCell(control) {
    let span = control.previousElementSibling;
    if (!span?.classList.contains('cell-display')) {
      span = document.createElement(control.dataset.field === 'title' ? 'a' : 'span');
      span.className = 'cell-display';
      if (control.dataset.field === 'title') span.href = control.closest('td').querySelector('.sheet-detail-link').href;
      control.before(span);
    }
    span.textContent = cellText(control);
    span.title = cellText(control);
    span.className = 'cell-display';
    if (['status', 'priority'].includes(control.dataset.field)) span.classList.add('badge', `${control.dataset.field}-${control.value}`);
  }
  root.querySelectorAll('[data-field]').forEach(refreshCell);
  root.classList.add('register-ready');
  function editing(on) {
    if (root.dataset.bulkSaving) return false;
    if (!on) {
      for (const control of root.querySelectorAll('[data-field]')) {
        if (ProjectWorkCells.value(control) !== control.savedValue && !control.disabled) {
          if (!control.checkValidity()) {control.reportValidity(); return false;}
          control.dispatchEvent(new Event('change', {bubbles:true}));
        }
      }
    }
    root.classList.toggle('register-editing', on);
    editButton.setAttribute('aria-pressed', String(on));
    editButton.textContent = on ? '✓ กลับโหมดอ่าน' : '✎ เปิดแก้ไขในตาราง';
    help.textContent = on ? 'Tab → ช่องถัดไป · Enter ↓ แถวถัดไป · Escape คืนค่าก่อนบันทึก · วางหลายช่องจาก Excel ได้ · Notes บันทึกด้วย Ctrl+Enter' : 'ดับเบิลคลิกช่องเพื่อแก้ไข · รองรับ Tab / Enter และวางหลายช่องจาก Excel';
    return true;
  }
  function layout(mode) {
    if (mode === 'cards' && !editing(false)) return;
    if (mode === 'cards' && document.body.classList.contains('register-focus')) focusTable(false);
    root.classList.toggle('register-cards', mode === 'cards');
    tableButton.setAttribute('aria-pressed', String(mode === 'table'));
    cardsButton.setAttribute('aria-pressed', String(mode === 'cards'));
  }
  layout(window.matchMedia('(max-width: 740px)').matches ? 'cards' : 'table');
  editButton.addEventListener('click', () => editing(!root.classList.contains('register-editing')));
  root.addEventListener('dblclick', event => {
    const td = event.target.closest('.spreadsheet td');
    const control = td?.querySelector('[data-field]:not(:disabled)');
    if (control && editing(true)) {control.focus(); if (control.tagName === 'INPUT' && control.type === 'text') control.select();}
  });
  tableButton.addEventListener('click', () => layout('table'));
  cardsButton.addEventListener('click', () => layout('cards'));
  root.addEventListener('projectwork:saved', event => {
    const row = event.detail.row;
    const card = root.querySelector(`[data-card-task="${row.dataset.taskId}"]`);
    row.querySelectorAll('[data-field]').forEach(control => {
      refreshCell(control);
      if (!card) return;
      const field = control.dataset.field.replace('_members','');
      const target = card.querySelector(`[data-card-field="${field}"]`);
      if (!target) return;
      const raw = control.savedValue ?? ProjectWorkCells.value(control);
      let text = cellText(control);
      if (field === 'progress') {
        text = raw + '%';
        card.querySelector('.progress-bar').style.width = raw + '%';
      }
      if (field === 'notes_to_colleague') {
        target.hidden = !raw;
        text = raw.length > 150 ? raw.slice(0,147) + '…' : raw;
      }
      if (field === 'project' && !raw) text = 'งานทั่วไป / ส่วนตัว';
      if (['sales','engineer'].includes(field) && !raw) text = 'ยังไม่มอบหมาย';
      if (field === 'due_date') text = 'กำหนดส่ง ' + (raw ? text : 'ไม่ระบุ');
      target.textContent = text;
      if (['status','priority'].includes(field)) target.className = `badge ${field}-${raw}`;
    });
    if (card) {
      const overdue = row.classList.contains('row-overdue');
      card.classList.toggle('card-overdue', overdue);
      const dueTarget = card.querySelector('[data-card-field="due_date"]');
      dueTarget.classList.toggle('overdue', overdue);
      const date = row.dataset.due;
      const formatted = date ? date.split('-').reverse().join('/') : 'ไม่ระบุ';
      dueTarget.textContent = (overdue ? 'เกินกำหนด · ' : '') + 'กำหนดส่ง ' + formatted;
    }
  });
})();
