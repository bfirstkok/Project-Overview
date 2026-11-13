(() => {
  const row = document.querySelector('#new-task-row');
  if (!row) return;
  const actions = document.querySelector('#new-task-row-actions');
  const fields = [...row.querySelectorAll('[data-new-field]')];
  const labels = Object.fromEntries(fields.map(field => [field.dataset.newField,field.getAttribute('aria-label').replace(' แถวใหม่','')]));
  const message = document.querySelector('#new-row-message');
  let requestId, busy = false, dirty = false;
  function open() {
    document.querySelector('#layout-table').click();
    if (row.hidden) {requestId = crypto.randomUUID(); row.hidden = actions.hidden = false;}
    fields.find(field => field.dataset.newField === 'title').focus();
    row.scrollIntoView({behavior:'smooth',block:'center'});
  }
  document.querySelector('#add-task-row').addEventListener('click',open);
  row.addEventListener('input',() => {dirty = true;});
  row.addEventListener('change',() => {dirty = true;});
  row.addEventListener('keydown',event => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {event.preventDefault();save(false);}
  });
  document.querySelector('#cancel-new-row').onclick = () => {
    if (busy) return;
    fields.forEach(field => {if (field.multiple) [...field.options].forEach(option => {option.selected = false;});else field.value = field.dataset.newField === 'progress' ? '0' : field.dataset.newField === 'priority' ? 'normal' : field.dataset.newField === 'status' ? 'todo' : '';field.dispatchEvent(new Event('change'));});
    row.hidden = actions.hidden = true;dirty = false;
  };
  async function save(again) {
    if (busy) return;
    for (const field of fields) if (!field.checkValidity()) {field.reportValidity();field.focus();return;}
    const data = Object.fromEntries(fields.map(field => [field.dataset.newField,field.multiple ? [...field.selectedOptions].map(option => option.value) : field.value]));
    busy = true;
    actions.querySelectorAll('button').forEach(button => {button.disabled = true;});
    row.querySelectorAll('input,select,textarea,button').forEach(field => {field.disabled = true;});
    message.textContent = 'กำลังบันทึกแถวใหม่…';
    try {
      const response = await fetch('/tasks/rows/new/',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':document.querySelector('#sheet-csrf input').value},body:JSON.stringify({request_id:requestId,fields:data})});
      const result = await response.json().catch(() => ({}));
      if (response.redirected || !response.ok) throw new Error(result.errors ? Object.entries(result.errors).map(([field,errors]) => `${labels[field] || 'ข้อมูลแถว'}: ${errors.join(' · ')}`).join(' | ') : result.error || 'บันทึกไม่ได้ กรุณาตรวจสิทธิ์หรือเข้าสู่ระบบใหม่');
      busy = dirty = false;
      const url = new URL('/tasks/',location.origin);url.searchParams.set('sort','-no');
      if (again) {url.searchParams.set('add_row','1');if (data.project) url.searchParams.set('new_project',data.project);}
      location.assign(url);
    } catch (error) {
      message.textContent = error.message + ' · ข้อมูลที่กรอกยังอยู่ หากเครือข่ายขัดข้องให้กดบันทึกซ้ำจากแถวนี้ได้';
      busy = false;
      actions.querySelectorAll('button').forEach(button => {button.disabled = false;});
      row.querySelectorAll('input,select,textarea,button').forEach(field => {field.disabled = false;});
    }
  }
  document.querySelector('#save-new-row').onclick = () => save(false);
  document.querySelector('#save-add-row').onclick = () => save(true);
  window.addEventListener('beforeunload',event => {if (busy || dirty) {event.preventDefault();event.returnValue = '';}});
  if (new URLSearchParams(location.search).get('add_row') === '1') open();
})();
