# DriveShare

A peer-to-peer car rental platform where owners list their cars and renters search, book, pay, message and review — built with Python (Flask), SQLite and server-rendered HTML/CSS.

The project's focus is software design: six classic design patterns are implemented and wired into real features rather than shown in isolation.

**Live demo:** https://driveshare-4m5e.onrender.com
Log in with `bob@demo.com` / `password123` (more demo accounts below). It's on Render's free plan, so the first visit can take up to a minute while the server wakes up, and the demo data resets whenever it restarts.

## Features

- **Accounts** with salted password hashing and three-question password recovery
- **Car listings** created step by step with the Builder pattern, editable by the owner, with an availability window
- **Search** by city, dates and max price, excluding cars that are already booked for the requested dates
- **Booking rules:** no past dates, no dates outside the owner's availability window, no overlapping reservations
- **Owner approval → payment → confirmation** flow with a demo wallet balance
- **Watchlist alerts** when a watched car drops in price or becomes available again
- **In-app messaging**, automatic booking messages, and a notifications feed
- **Reviews** limited to renters with a paid rental, one review per car
- **Rental history** for both renters and owners
- **Responsive layout** for desktop, tablet and phone

## Design Patterns

| Pattern | Where (`app.py`) | What it does |
| --- | --- | --- |
| **Singleton** | `UserSession` | One session manager handles all login, logout and auth checks |
| **Observer** | `CarListingSubject`, `WatchlistObserver` | Notifies renters watching a car about price drops, bookings and re-listings |
| **Mediator** | `DriveShareMediator` | Coordinates the Search, Booking and Message components so they never call each other directly |
| **Builder** | `ConcreteCarBuilder` | Builds and validates a car listing step by step |
| **Proxy** | `PaymentProxy` | Validates and audit-logs every payment before delegating to the real payment service |
| **Chain of Responsibility** | `Question1/2/3Handler` | Password recovery passes through three security-question handlers in order |

## Demo Accounts

The database is created and filled with demo data automatically on first run.

| Name | Email | Password | Role |
| --- | --- | --- | --- |
| Alice Owner | alice@demo.com | password123 | Owner |
| Bob Renter | bob@demo.com | password123 | Renter |
| Carol Driver | carol@demo.com | password123 | Owner and renter |

Security question answers (lowercase): Alice — fluffy / chicago / smith · Bob — rex / detroit / jones · Carol — whiskers / miami / brown

## Built With

- Python 3 and Flask
- SQLite
- Jinja2 templates with hand-written CSS
- Werkzeug password hashing
- Gunicorn and Render for deployment

## Run Locally

1. Clone the repo and open the folder:
   ```bash
   git clone https://github.com/mberry-dev/driveshare.git
   cd driveshare
   ```
2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the app:
   ```bash
   python app.py
   ```
4. Open http://127.0.0.1:5000 in your browser.

To reset the demo data, stop the app, delete `instance/driveshare.db`, and start it again.

## Deploy to Render

The repo includes a `render.yaml` blueprint. In Render, choose **New → Blueprint**, connect this repository, and deploy. Render installs the requirements, starts the app with Gunicorn, and generates a `SECRET_KEY` automatically.

On Render's free plan the SQLite file is temporary, so the demo resets to clean data whenever the service restarts or wakes from sleep.

## Project Structure

```
driveshare/
├── app.py              # Routes and all six design patterns
├── database.py         # Schema, connection handling and demo seed data
├── requirements.txt    # Flask and Gunicorn
├── render.yaml         # Render deployment blueprint
├── templates/          # Jinja2 pages (home, search, car detail, dashboard, messages, …)
├── static/             # Placeholder image for cars without a photo
├── instance/           # SQLite database (created on first run, not committed)
├── reports/            # Project reports
└── presentation/       # Project presentation
```

## Background

DriveShare began as the term project for CIS 476 (Software Design Patterns) at the University of Michigan-Dearborn and has since been cleaned up for deployment as a portfolio demo.
