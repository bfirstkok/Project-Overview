(() => {
  const calendar = document.querySelector('.work-calendar');
  if (!calendar) return;
  calendar.querySelectorAll('[data-calendar-day]').forEach(button => {
    button.addEventListener('click', () => {
      const date = button.dataset.calendarDay;
      calendar.querySelectorAll('[data-agenda-day]').forEach(day => {day.hidden = day.dataset.agendaDay !== date;});
      calendar.querySelectorAll('.calendar-date-select').forEach(day => {
        const selected = day.dataset.calendarDay === date;
        day.setAttribute('aria-pressed', String(selected));
        day.closest('.work-calendar-day').classList.toggle('is-selected', selected);
      });
      const url = new URL(window.location.href);
      url.searchParams.set('day', date);
      history.replaceState(null, '', url);
      if (window.matchMedia('(max-width: 1000px)').matches) calendar.querySelector('.calendar-agenda').scrollIntoView({behavior:'smooth',block:'start'});
    });
  });
  document.querySelector('#calendar-month-picker')?.addEventListener('change', event => {
    if (!/^\d{4}-\d{2}$/.test(event.target.value)) return;
    const [year, month] = event.target.value.split('-');
    const url = new URL(window.location.href);
    url.searchParams.set('year',year); url.searchParams.set('month',month);
    url.searchParams.delete('day'); url.searchParams.delete('page');
    window.location.assign(url);
  });
})();
