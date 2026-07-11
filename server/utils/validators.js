const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function isValidEmail(email) {
  return typeof email === 'string' && EMAIL_RE.test(email.trim()) && email.length <= 254;
}

function isValidPassword(password) {
  return typeof password === 'string' && password.length >= 8 && password.length <= 128;
}

function isValidName(name) {
  return typeof name === 'string' && name.trim().length >= 2 && name.trim().length <= 80;
}

module.exports = { isValidEmail, isValidPassword, isValidName };
