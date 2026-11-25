
const search = document.querySelector('#projectSearch');
const cards = [...document.querySelectorAll('[data-search]')];
const counter = document.querySelector('#projectCount');
const update = () => {
  const q = (search?.value || '').trim().toLowerCase();
  let shown = 0;
  for (const card of cards) {
    const match = !q || card.dataset.search.includes(q);
    card.classList.toggle('hidden', !match);
    if (match) shown++;
  }
  if (counter) counter.textContent = `${shown} 個項目`;
};
search?.addEventListener('input', update);
update();
