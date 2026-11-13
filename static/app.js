(() => {
  const theme = localStorage.getItem('projectwork-theme');
  if (theme === 'dark') document.documentElement.dataset.theme = 'dark';
  document.querySelector('#theme-toggle')?.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    localStorage.setItem('projectwork-theme', next);
    drawChart();
  });
  document.querySelector('.mobile-menu')?.addEventListener('click', event => {
    const open = document.querySelector('#sidebar').classList.toggle('open');
    event.currentTarget.setAttribute('aria-expanded', String(open));
  });
  function drawChart() {
    const canvas = document.querySelector('#status-chart');
    const dataNode = document.querySelector('#chart-data');
    if (!canvas || !dataNode) return;
    const data = JSON.parse(dataNode.textContent);
    const total = data.reduce((sum, item) => sum + item.value, 0);
    const ctx = canvas.getContext('2d');
    const colors = {todo: '#b9c6d6', progress: '#4a81c7', hold: '#e7af51', done: '#269a7e', cancelled: '#969ba3'};
    ctx.clearRect(0, 0, 220, 220);
    ctx.lineWidth = 23;
    let angle = -Math.PI / 2;
    if (!total) {ctx.beginPath(); ctx.strokeStyle = '#e6ebef'; ctx.arc(110, 110, 86, 0, Math.PI * 2); ctx.stroke();}
    data.forEach(item => {
      if (!item.value) return;
      const arc = item.value / total * Math.PI * 2;
      const gap = Math.min(0.025,arc/4);
      ctx.beginPath(); ctx.strokeStyle = colors[item.key];
      ctx.arc(110, 110, 86, angle + gap, angle + arc - gap);
      ctx.stroke(); angle += arc;
    });
  }
  drawChart();
})();

// Serialize edits per row; compare the database version for every mutation.
(() => {
  const message = document.querySelector('#sheet-message');
  if (!message) return;
  const token = document.querySelector('#sheet-csrf input').value;
  let pending = 0;
  document.querySelectorAll('.sheet-row').forEach(row => {
    row.saveQueue = Promise.resolve();
    row.querySelectorAll('[data-field]').forEach(control => {
      control.savedValue = ProjectWorkCells.value(control);
      const save = () => {
        if (ProjectWorkCells.value(control) === control.savedValue || control.disabled || row.dataset.conflict || document.querySelector('#task-register')?.dataset.bulkSaving) return;
        if (!control.checkValidity()) { control.reportValidity(); return; }
        const value = ProjectWorkCells.value(control);
        const previous = control.savedValue;
        control.disabled = true;
        pending += 1;
        row.saveQueue = row.saveQueue.then(async () => {
          if (row.dataset.conflict) return;
          message.textContent = 'กำลังบันทึกงาน #' + row.dataset.taskId + '…';
          try {
            const response = await fetch(row.dataset.updateUrl, {
              method: 'POST', credentials: 'same-origin',
              headers: {'Content-Type':'application/json', 'X-CSRFToken':token},
              body: JSON.stringify({field:control.dataset.field,value:ProjectWorkCells.payload(control,value),version:Number(row.dataset.version)})
            });
            const result = await response.json().catch(() => ({}));
            if (response.redirected) {message.textContent = 'Session หมดอายุ กรุณาเข้าสู่ระบบใหม่'; return;}
            if (response.status === 409) {
              row.dataset.conflict = 'true'; row.classList.add('row-conflict');
              row.querySelectorAll('[data-field]').forEach(el => {el.disabled = true;});
              message.textContent = 'มีคนแก้งาน #' + row.dataset.taskId + ' แล้ว — ค่าที่คุณพิมพ์ยังไม่ถูกบันทึก กรุณาเปิดรายละเอียดล่าสุดเปรียบเทียบและโหลดใหม่';
              return;
            }
            if (!response.ok) {
              ProjectWorkCells.restore(control,previous); control.dispatchEvent(new CustomEvent('projectwork:restored'));
              const details = result.errors ? Object.values(result.errors).flat().join(' · ') : result.error || 'ไม่มีสิทธิ์หรือ session หมดอายุ';
              message.textContent = 'บันทึกไม่ได้: ' + details;
              return;
            }
            if (typeof result.version !== 'number') throw new Error('Invalid response');
            row.dataset.version = String(result.version);
            control.savedValue = value;
            message.textContent = '✓ บันทึกงาน #' + row.dataset.taskId + ' เรียบร้อยแล้ว';
            const progress = row.querySelector('.progress-bar');
            progress.style.width = result.progress + '%';
            progress.parentElement.setAttribute('aria-valuenow', result.progress);
            if (control.dataset.field === 'status') control.className = 'status-' + result.status;
            if (control.dataset.field === 'priority') control.className = 'priority-' + value;
            const status = row.querySelector('[data-field="status"]')?.value || row.dataset.status;
            const priority = row.querySelector('[data-field="priority"]')?.value || row.dataset.priority;
            const due = row.querySelector('[data-field="due_date"]')?.value ?? row.dataset.due;
            const today = new Intl.DateTimeFormat('en-CA', {timeZone:'Asia/Bangkok'}).format(new Date());
            row.classList.remove('row-complete','row-cancelled','row-overdue','row-urgent');
            if (status === 'done') row.classList.add('row-complete');
            else if (status === 'cancelled') row.classList.add('row-cancelled');
            else if (due && due < today) row.classList.add('row-overdue');
            else if (['high','critical'].includes(priority)) row.classList.add('row-urgent');
            row.dataset.status = status; row.dataset.priority = priority; row.dataset.due = due;
            row.dispatchEvent(new CustomEvent('projectwork:saved', {bubbles:true,detail:{row}}));
          } catch (error) {
            message.textContent = 'การเชื่อมต่อขัดข้อง กรุณาโหลดข้อมูลล่าสุดเพื่อตรวจว่าบันทึกสำเร็จหรือไม่';
          }
        }).finally(() => { pending -= 1; if (!row.dataset.conflict) control.disabled = false; });
      };
      control.addEventListener('change', save);
      control.addEventListener('keydown', event => {
        if (event.key === 'Enter' && (control.tagName !== 'TEXTAREA' || event.ctrlKey || event.metaKey)) {event.preventDefault(); save();}
      });
    });
  });
  window.addEventListener('beforeunload', event => {if (pending) {event.preventDefault(); event.returnValue = '';}});
})();
