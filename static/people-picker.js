(() => {
  document.querySelectorAll('select[multiple][data-field]').forEach(select => {
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'people-picker-button';
    button.setAttribute('aria-label','เลือกหลายคน · ' + select.getAttribute('aria-label'));
    button.setAttribute('aria-haspopup','dialog');
    const render = () => {
      button.textContent = [...select.selectedOptions].map(option => option.textContent).join(', ') || 'เลือกคนทำงาน…';
      button.disabled = select.disabled;
    };
    select.after(button); select.classList.add('people-picker-source'); render();
    new MutationObserver(render).observe(select,{attributes:true,attributeFilter:['disabled']});
    select.addEventListener('change',render);
    select.addEventListener('projectwork:restored',render);
    document.querySelector('#task-register')?.addEventListener('projectwork:saved',render);
    button.onclick = () => {
      if (select.disabled) return;
      const dialog = document.createElement('dialog'); dialog.className = 'grid-preview people-picker-dialog';
      const heading = document.createElement('h2'); heading.textContent = select.getAttribute('aria-label');
      const hint = document.createElement('p'); hint.textContent = 'ติ๊กเลือกได้หลายคน · ยังไม่บันทึกจนกว่าจะกดปุ่มบันทึก';
      const options = document.createElement('div'); options.className = 'people-picker-options';
      for (const option of select.options) {
        const label = document.createElement('label');
        const checkbox = document.createElement('input'); checkbox.type = 'checkbox';checkbox.value = option.value;checkbox.checked = option.selected;
        const name = document.createElement('span');name.textContent = option.textContent;
        label.append(checkbox,name);options.append(label);
      }
      const cancel = document.createElement('button');cancel.type='button';cancel.className='btn btn-outline-secondary';cancel.textContent='ยกเลิก';
      const save = document.createElement('button');save.type='button';save.className='btn btn-primary';save.textContent='บันทึกผู้รับผิดชอบ';
      cancel.onclick = () => dialog.close();
      save.onclick = () => {
        if (select.disabled || select.closest('tr').dataset.conflict) {dialog.close();return;}
        const selected = [...options.querySelectorAll('input:checked')].map(input => input.value);
        [...select.options].forEach(option => {option.selected = selected.includes(option.value);});
        select.dispatchEvent(new Event('change',{bubbles:true}));render();dialog.close();
      };
      dialog.addEventListener('close',() => {dialog.remove();button.focus();});
      dialog.append(heading,hint,options,cancel,save);document.body.append(dialog);dialog.showModal();
    };
  });
})();
