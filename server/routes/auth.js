const express = require('express');
const crypto = require('crypto');
const bcrypt = require('bcryptjs');
const rateLimit = require('express-rate-limit');

const { findByEmail, createUser, updateUser } = require('../utils/userStore');
const { isValidEmail, isValidPassword, isValidName } = require('../utils/validators');
const { signToken, cookieOptions } = require('../utils/tokens');
const { requireAuth, COOKIE_NAME } = require('../middleware/requireAuth');

const router = express.Router();

const MAX_FAILED_ATTEMPTS = 5;
const LOCK_DURATION_MS = 15 * 60 * 1000; // 15 minutes

const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  limit: 20,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Too many attempts. Please try again later.' },
});

function publicUser(user) {
  return { id: user.id, name: user.name, email: user.email, company: user.company || '' };
}

router.post('/register', authLimiter, (req, res) => {
  const { name, email, password, company } = req.body || {};

  if (!isValidName(name)) {
    return res.status(400).json({ error: 'Please enter your full name (2-80 characters).' });
  }
  if (!isValidEmail(email)) {
    return res.status(400).json({ error: 'Please enter a valid email address.' });
  }
  if (!isValidPassword(password)) {
    return res.status(400).json({ error: 'Password must be at least 8 characters long.' });
  }
  if (findByEmail(email)) {
    return res.status(409).json({ error: 'An account with this email already exists.' });
  }

  const passwordHash = bcrypt.hashSync(password, 12);
  const user = createUser({
    id: crypto.randomUUID(),
    name: name.trim(),
    email,
    passwordHash,
    company: (company || '').trim(),
  });

  const token = signToken({ sub: user.id, email: user.email, name: user.name });
  res.cookie(COOKIE_NAME, token, cookieOptions());
  return res.status(201).json({ user: publicUser(user) });
});

router.post('/login', authLimiter, (req, res) => {
  const { email, password } = req.body || {};

  if (!isValidEmail(email) || typeof password !== 'string' || password.length === 0) {
    return res.status(400).json({ error: 'Please enter a valid email and password.' });
  }

  const user = findByEmail(email);

  // Constant-shape response to avoid leaking which emails are registered.
  const genericError = { error: 'Invalid email or password.' };

  if (!user) {
    bcrypt.hashSync('dummy-password-for-timing', 12); // keep timing consistent
    return res.status(401).json(genericError);
  }

  if (user.lockedUntil && new Date(user.lockedUntil) > new Date()) {
    const minutesLeft = Math.ceil((new Date(user.lockedUntil) - new Date()) / 60000);
    return res.status(423).json({
      error: `Account temporarily locked due to repeated failed attempts. Try again in ${minutesLeft} minute(s).`,
    });
  }

  const passwordMatches = bcrypt.compareSync(password, user.passwordHash);

  if (!passwordMatches) {
    const failedAttempts = (user.failedAttempts || 0) + 1;
    const lockedUntil =
      failedAttempts >= MAX_FAILED_ATTEMPTS ? new Date(Date.now() + LOCK_DURATION_MS).toISOString() : null;
    updateUser(user.id, { failedAttempts, lockedUntil });
    return res.status(401).json(genericError);
  }

  updateUser(user.id, { failedAttempts: 0, lockedUntil: null });

  const token = signToken({ sub: user.id, email: user.email, name: user.name });
  res.cookie(COOKIE_NAME, token, cookieOptions());
  return res.json({ user: publicUser(user) });
});

router.post('/logout', (req, res) => {
  res.clearCookie(COOKIE_NAME, { path: '/' });
  return res.json({ ok: true });
});

router.get('/me', requireAuth, (req, res) => {
  const user = findByEmail(req.user.email);
  if (!user) {
    return res.status(401).json({ error: 'Not authenticated.' });
  }
  return res.json({ user: publicUser(user) });
});

module.exports = router;
