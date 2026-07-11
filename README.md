# Rajmait — IT Consulting Website

A three-page marketing site (Home, About, Services) plus a real authenticated
client portal, built with a static frontend and an Express backend.

## Stack

- **Frontend:** semantic HTML, hand-written CSS (no framework), vanilla JS
- **Backend:** Node.js + Express
- **Auth:** bcrypt-hashed passwords, JWT stored in an httpOnly/SameSite=strict
  cookie, per-account lockout after repeated failed logins, rate-limited
  auth endpoints, Helmet security headers
- **Storage:** a JSON file (`data/users.json`, gitignored) — swap for a real
  database in production

## Getting started

```bash
npm install
cp .env.example .env   # then set a strong random JWT_SECRET
npm start
```

The app runs at `http://localhost:3000`.

On first run a demo account is seeded automatically:

- Email: `demo@rajmait.com`
- Password: `Demo@12345`

## Pages

| Route            | Description                                   |
|-------------------|------------------------------------------------|
| `/`                | Home                                           |
| `/about.html`      | About / team / values                          |
| `/services.html`   | Services, engagement models, contact form      |
| `/login.html`      | Login + account creation                        |
| `/dashboard`        | Authenticated client portal (server-protected) |

## API

| Method & Path            | Description                          |
|---------------------------|---------------------------------------|
| `POST /api/auth/register` | Create an account, sets session cookie |
| `POST /api/auth/login`    | Log in, sets session cookie            |
| `POST /api/auth/logout`   | Clears session cookie                  |
| `GET  /api/auth/me`       | Returns the current user (401 if not signed in) |

## Notes for production

- Replace the JSON file store with a real database.
- Set `NODE_ENV=production` (enables `secure` cookies) and serve over HTTPS.
- Rotate `JWT_SECRET` to a long random value and keep it out of version control.
