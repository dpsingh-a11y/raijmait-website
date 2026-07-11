(function () {
  const navbar = document.querySelector('.navbar');
  const toggle = document.querySelector('.nav-toggle');

  if (toggle && navbar) {
    toggle.addEventListener('click', () => {
      const isOpen = navbar.classList.toggle('nav-open');
      toggle.setAttribute('aria-expanded', String(isOpen));
    });
  }

  const yearEl = document.getElementById('year');
  if (yearEl) {
    yearEl.textContent = new Date().getFullYear();
  }

  // Reflect signed-in state in the nav (Login link becomes Dashboard/Logout).
  fetch('/api/auth/me', { credentials: 'same-origin' })
    .then((res) => (res.ok ? res.json() : null))
    .then((data) => {
      if (!data || !data.user) return;
      document.querySelectorAll('[data-auth-link]').forEach((el) => {
        el.textContent = 'Client Portal';
        el.setAttribute('href', '/dashboard');
      });
    })
    .catch(() => {});
})();
