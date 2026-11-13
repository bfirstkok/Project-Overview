window.ProjectWorkCells = {
  value(control) {return control.multiple ? JSON.stringify([...control.selectedOptions].map(option => option.value)) : control.value;},
  restore(control,value) {
    if (control.multiple) {const values = JSON.parse(value || '[]'); [...control.options].forEach(option => {option.selected = values.includes(option.value);});}
    else control.value = value;
  },
  payload(control,value) {return control.multiple ? JSON.parse(value) : value;}
};
