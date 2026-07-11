const fs = require('fs');
const path = require('path');

const DB_PATH = path.join(__dirname, '..', '..', 'data', 'users.json');

function ensureStore() {
  if (!fs.existsSync(DB_PATH)) {
    fs.mkdirSync(path.dirname(DB_PATH), { recursive: true });
    fs.writeFileSync(DB_PATH, '[]', 'utf8');
  }
}

function readAll() {
  ensureStore();
  const raw = fs.readFileSync(DB_PATH, 'utf8');
  try {
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

function writeAll(users) {
  ensureStore();
  const tmpPath = `${DB_PATH}.tmp`;
  fs.writeFileSync(tmpPath, JSON.stringify(users, null, 2), 'utf8');
  fs.renameSync(tmpPath, DB_PATH);
}

function findByEmail(email) {
  const normalized = email.trim().toLowerCase();
  return readAll().find((u) => u.email === normalized) || null;
}

function createUser({ id, name, email, passwordHash, company = '' }) {
  const users = readAll();
  const user = {
    id,
    name,
    email: email.trim().toLowerCase(),
    company,
    passwordHash,
    createdAt: new Date().toISOString(),
    failedAttempts: 0,
    lockedUntil: null,
  };
  users.push(user);
  writeAll(users);
  return user;
}

function updateUser(id, updates) {
  const users = readAll();
  const idx = users.findIndex((u) => u.id === id);
  if (idx === -1) return null;
  users[idx] = { ...users[idx], ...updates };
  writeAll(users);
  return users[idx];
}

module.exports = { readAll, writeAll, findByEmail, createUser, updateUser };
