require('dotenv').config();

const path = require('path');
const express = require('express');
const helmet = require('helmet');
const compression = require('compression');
const cookieParser = require('cookie-parser');

const authRoutes = require('./routes/auth');
const { requirePageAuth } = require('./middleware/requireAuth');
const { seedDemoUser } = require('./utils/seedDemoUser');

seedDemoUser();

const app = express();
const PORT = process.env.PORT || 3000;
const PUBLIC_DIR = path.join(__dirname, '..', 'public');

app.disable('x-powered-by');
app.set('trust proxy', 1);

app.use(
  helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        scriptSrc: ["'self'"],
        styleSrc: ["'self'", "'unsafe-inline'"],
        imgSrc: ["'self'", 'data:'],
        connectSrc: ["'self'"],
        objectSrc: ["'none'"],
        baseUri: ["'self'"],
        frameAncestors: ["'self'"],
      },
    },
    referrerPolicy: { policy: 'strict-origin-when-cross-origin' },
  })
);
app.use(compression());
app.use(express.json({ limit: '10kb' }));
app.use(cookieParser());

app.use(
  express.static(PUBLIC_DIR, {
    extensions: ['html'],
    setHeaders: (res, filePath) => {
      if (/\.(css|js)$/.test(filePath)) {
        res.setHeader('Cache-Control', 'public, max-age=3600');
      }
    },
  })
);

app.use('/api/auth', authRoutes);

// Protected page: dashboard.html itself is not in /public, so it can only be
// reached through this authenticated route.
app.get(['/dashboard', '/dashboard.html'], requirePageAuth, (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'views', 'dashboard.html'));
});

app.use((req, res) => {
  res.status(404).sendFile(path.join(PUBLIC_DIR, '404.html'));
});

app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: 'Something went wrong. Please try again.' });
});

app.listen(PORT, () => {
  console.log(`Rajmait website running at http://localhost:${PORT}`);
});
