const http = require('node:http');

const loginPage = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>PrepChef Login</title>
    <style>
      body { font-family: sans-serif; margin: 2rem; }
      form { display: flex; flex-direction: column; gap: 0.75rem; max-width: 320px; }
      label { display: flex; flex-direction: column; font-size: 0.9rem; }
      input { padding: 0.5rem; font-size: 1rem; }
      button { padding: 0.5rem; font-size: 1rem; cursor: pointer; }
    </style>
  </head>
  <body>
    <h1>Login</h1>
    <form id="login-form">
      <label>Email
        <input name="email" type="email" autocomplete="email" />
      </label>
      <label>Password
        <input name="password" type="password" autocomplete="current-password" />
      </label>
      <button type="submit">Sign in</button>
    </form>
    <script>
      document.getElementById('login-form').addEventListener('submit', function (event) {
        event.preventDefault();
        window.location.href = '/dashboard';
      });
    </script>
  </body>
</html>`;

const dashboardPage = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Dashboard</title>
  </head>
  <body>
    <h1>Welcome to PrepChef</h1>
    <p id="welcome-message">You are logged in.</p>
  </body>
</html>`;

const bookingsPage = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Bookings</title>
    <style>
      body { font-family: sans-serif; margin: 2rem; }
      .hidden { display: none; }
      form { display: flex; flex-direction: column; gap: 0.75rem; max-width: 320px; margin-top: 1rem; }
      input { padding: 0.5rem; font-size: 1rem; }
      button { padding: 0.5rem; font-size: 1rem; cursor: pointer; }
      #confirmation { margin-top: 1rem; font-weight: bold; color: #0f7a0f; }
    </style>
  </head>
  <body>
    <h1>Bookings</h1>
    <button id="new-booking" type="button">New Booking</button>
    <form id="booking-form" class="hidden">
      <label>Date
        <input name="date" type="date" />
      </label>
      <button type="submit">Submit</button>
    </form>
    <div id="confirmation" class="hidden">Booking confirmed</div>
    <script>
      const trigger = document.getElementById('new-booking');
      const form = document.getElementById('booking-form');
      const confirmation = document.getElementById('confirmation');

      trigger.addEventListener('click', function () {
        form.classList.remove('hidden');
        confirmation.classList.add('hidden');
      });

      form.addEventListener('submit', function (event) {
        event.preventDefault();
        confirmation.classList.remove('hidden');
      });
    </script>
  </body>
</html>`;

const routes = new Map([
  ['/login', loginPage],
  ['/dashboard', dashboardPage],
  ['/bookings', bookingsPage],
]);

const port = Number(process.env.PORT || 3000);

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  if (req.method === 'GET' && routes.has(url.pathname)) {
    const body = routes.get(url.pathname);
    res.writeHead(200, {
      'Content-Type': 'text/html; charset=utf-8',
      'Content-Length': Buffer.byteLength(body),
    });
    res.end(body);
    return;
  }

  if (req.method === 'GET' && url.pathname === '/healthz') {
    const payload = JSON.stringify({ ok: true, svc: 'web' });
    res.writeHead(200, {
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(payload),
    });
    res.end(payload);
    return;
  }

  res.statusCode = 404;
  res.end('Not found');
});

server.listen(port, () => {
  // eslint-disable-next-line no-console
  console.log(`web server listening on ${port}`);
});
