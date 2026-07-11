const bcrypt = require('bcryptjs');
const crypto = require('crypto');
const { findByEmail, createUser } = require('./userStore');

const DEMO_EMAIL = 'demo@rajmait.com';
const DEMO_PASSWORD = 'Demo@12345';

function seedDemoUser() {
  if (findByEmail(DEMO_EMAIL)) return;
  createUser({
    id: crypto.randomUUID(),
    name: 'Demo Client',
    email: DEMO_EMAIL,
    passwordHash: bcrypt.hashSync(DEMO_PASSWORD, 12),
    company: 'Rajmait Demo Account',
  });
  console.log(`Seeded demo account -> ${DEMO_EMAIL} / ${DEMO_PASSWORD}`);
}

module.exports = { seedDemoUser, DEMO_EMAIL, DEMO_PASSWORD };
