# Prep

This repository contains a simple kitchen rental MVP with a Node/Express backend and a React frontend.

## Backend

1. `cd backend`
2. Create `.env` with your `DATABASE_URL` and `PORT`.
3. Run `npm install` to install dependencies (requires network access).
4. `npm start` will launch the server on the configured port.

The backend exposes:
- `GET /kitchens`
- `GET /kitchens/:id`
- `POST /bookings`
- `GET /admin/certs`

## Frontend

1. `cd frontend`
2. Create `.env` with `VITE_API_BASE_URL`.
3. Run `npm install` to install dependencies.
4. `npm run dev` starts the development server.

The frontend fetches kitchens and allows submitting a mocked booking.
