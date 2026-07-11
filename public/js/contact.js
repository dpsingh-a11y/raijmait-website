(function () {
  const form = document.getElementById('contact-form');
  const success = document.getElementById('contact-success');
  if (!form) return;

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }
    success.classList.add('visible');
    form.reset();
    success.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  });
})();
