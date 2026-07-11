(function () {
  const tabLogin = document.getElementById('tab-login');
  const tabRegister = document.getElementById('tab-register');
  const panelLogin = document.getElementById('panel-login');
  const panelRegister = document.getElementById('panel-register');
  const formError = document.getElementById('form-error');

  function activateTab(tab) {
    const isLogin = tab === 'login';
    tabLogin.classList.toggle('active', isLogin);
    tabRegister.classList.toggle('active', !isLogin);
    tabLogin.setAttribute('aria-selected', String(isLogin));
    tabRegister.setAttribute('aria-selected', String(!isLogin));
    panelLogin.classList.toggle('active', isLogin);
    panelRegister.classList.toggle('active', !isLogin);
    hideError();
  }

  tabLogin.addEventListener('click', () => activateTab('login'));
  tabRegister.addEventListener('click', () => activateTab('register'));

  function showError(message) {
    formError.textContent = message;
    formError.classList.add('visible');
  }

  function hideError() {
    formError.classList.remove('visible');
  }

  function getRedirectTarget() {
    const params = new URLSearchParams(window.location.search);
    const redirect = params.get('redirect');
    return redirect && redirect.startsWith('/') ? redirect : '/dashboard';
  }

  async function submitJSON(url, payload) {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.error || 'Something went wrong. Please try again.');
    }
    return data;
  }

  // Password visibility toggles
  document.querySelectorAll('.password-toggle').forEach((btn) => {
    btn.addEventListener('click', () => {
      const input = document.getElementById(btn.dataset.toggleFor);
      const isHidden = input.type === 'password';
      input.type = isHidden ? 'text' : 'password';
      btn.textContent = isHidden ? 'Hide' : 'Show';
    });
  });

  // Password strength meter
  const registerPassword = document.getElementById('register-password');
  const strengthBar = document.getElementById('strength-bar');
  if (registerPassword && strengthBar) {
    registerPassword.addEventListener('input', () => {
      const value = registerPassword.value;
      let score = 0;
      if (value.length >= 8) score += 1;
      if (value.length >= 12) score += 1;
      if (/[A-Z]/.test(value) && /[a-z]/.test(value)) score += 1;
      if (/\d/.test(value)) score += 1;
      if (/[^A-Za-z0-9]/.test(value)) score += 1;

      const pct = Math.min((score / 5) * 100, 100);
      strengthBar.style.width = `${pct}%`;
      strengthBar.style.background =
        score <= 1 ? '#d92d20' : score <= 3 ? '#dc6803' : '#12b76a';
    });
  }

  // Demo account autofill
  const demoFill = document.getElementById('demo-fill');
  if (demoFill) {
    demoFill.addEventListener('click', (event) => {
      event.preventDefault();
      document.getElementById('login-email').value = 'demo@rajmait.com';
      document.getElementById('login-password').value = 'Demo@12345';
    });
  }

  // Login submit
  panelLogin.addEventListener('submit', async (event) => {
    event.preventDefault();
    hideError();
    const submitBtn = document.getElementById('login-submit');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Signing in…';
    try {
      await submitJSON('/api/auth/login', {
        email: document.getElementById('login-email').value.trim(),
        password: document.getElementById('login-password').value,
      });
      window.location.href = getRedirectTarget();
    } catch (err) {
      showError(err.message);
      submitBtn.disabled = false;
      submitBtn.textContent = 'Log In';
    }
  });

  // Register submit
  panelRegister.addEventListener('submit', async (event) => {
    event.preventDefault();
    hideError();
    const submitBtn = document.getElementById('register-submit');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Creating account…';
    try {
      await submitJSON('/api/auth/register', {
        name: document.getElementById('register-name').value.trim(),
        company: document.getElementById('register-company').value.trim(),
        email: document.getElementById('register-email').value.trim(),
        password: document.getElementById('register-password').value,
      });
      window.location.href = getRedirectTarget();
    } catch (err) {
      showError(err.message);
      submitBtn.disabled = false;
      submitBtn.textContent = 'Create Account';
    }
  });

  // If already signed in, skip straight to the dashboard.
  fetch('/api/auth/me', { credentials: 'same-origin' })
    .then((res) => (res.ok ? res.json() : null))
    .then((data) => {
      if (data && data.user) {
        window.location.href = getRedirectTarget();
      }
    })
    .catch(() => {});
})();
