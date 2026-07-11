const { verifyToken } = require('../utils/tokens');

const COOKIE_NAME = process.env.COOKIE_NAME || 'rajmait_session';

function requireAuth(req, res, next) {
  const token = req.cookies?.[COOKIE_NAME];
  if (!token) {
    return res.status(401).json({ error: 'Not authenticated.' });
  }
  try {
    const decoded = verifyToken(token);
    req.user = { id: decoded.sub, email: decoded.email, name: decoded.name };
    next();
  } catch {
    res.clearCookie(COOKIE_NAME, { path: '/' });
    return res.status(401).json({ error: 'Session expired. Please log in again.' });
  }
}

function requirePageAuth(req, res, next) {
  const token = req.cookies?.[COOKIE_NAME];
  if (!token) {
    return res.redirect('/login.html?redirect=/dashboard');
  }
  try {
    const decoded = verifyToken(token);
    req.user = { id: decoded.sub, email: decoded.email, name: decoded.name };
    next();
  } catch {
    res.clearCookie(COOKIE_NAME, { path: '/' });
    return res.redirect('/login.html?redirect=/dashboard');
  }
}

module.exports = { requireAuth, requirePageAuth, COOKIE_NAME };
