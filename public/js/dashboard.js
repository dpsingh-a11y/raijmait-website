(function () {
  const heading = document.getElementById('welcome-heading');
  const nameEl = document.getElementById('account-name');
  const emailEl = document.getElementById('account-email');
  const companyEl = document.getElementById('account-company');
  const logoutBtn = document.getElementById('logout-btn');

  fetch('/api/auth/me', { credentials: 'same-origin' })
    .then((res) => {
      if (!res.ok) throw new Error('unauthenticated');
      return res.json();
    })
    .then(({ user }) => {
      const firstName = user.name.split(' ')[0];
      heading.textContent = `Welcome back, ${firstName}`;
      nameEl.textContent = user.name;
      emailEl.textContent = user.email;
      companyEl.textContent = user.company || '';
    })
    .catch(() => {
      window.location.href = '/login.html?redirect=/dashboard';
    });

  logoutBtn.addEventListener('click', async () => {
    logoutBtn.disabled = true;
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin' }).catch(() => {});
    window.location.href = '/login.html';
  });
})();
