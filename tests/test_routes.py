"""Tests for pages and user flows: auth, recovery, booking, payment, reviews, messaging."""
import hashlib

import pytest

from conftest import login, days_from_today as D


def text(resp):
    return resp.get_data(as_text=True)


@pytest.mark.parametrize('url', ['/', '/search?show_all=1', '/search?location=Miami',
                                 '/cars/1', '/login', '/register', '/recover'])
def test_public_pages_load(client, url):
    assert client.get(url).status_code == 200


def test_home_shows_real_stats(client):
    html = text(client.get('/'))
    assert '>10<' in html and '500+' not in html


@pytest.mark.parametrize('url', ['/dashboard', '/messages', '/history', '/cars/new'])
def test_protected_pages_require_login(client, url):
    assert '/login' in client.get(url).headers['Location']


# ── Authentication ──────────────────────────────────────────────

@pytest.mark.parametrize('email', ['alice@demo.com', 'bob@demo.com', 'carol@demo.com'])
def test_demo_logins(client, email):
    assert 'Welcome back' in text(login(client, email))


def test_wrong_password_rejected(client):
    assert 'Invalid email or password' in text(login(client, 'bob@demo.com', 'nope'))


def test_passwords_stored_salted(db_conn):
    pw = db_conn.execute("SELECT password FROM users WHERE email='bob@demo.com'").fetchone()[0]
    assert pw.startswith(('scrypt:', 'pbkdf2:'))


def test_legacy_hash_login_upgrades(client, db_conn):
    db_conn.execute("UPDATE users SET password=? WHERE email='carol@demo.com'",
                    (hashlib.sha256(b'password123').hexdigest(),)); db_conn.commit()
    assert 'Welcome back' in text(login(client, 'carol@demo.com'))
    pw = db_conn.execute("SELECT password FROM users WHERE email='carol@demo.com'").fetchone()[0]
    assert pw.startswith(('scrypt:', 'pbkdf2:'))


def test_register_and_password_recovery(app):
    c = app.test_client()
    c.post('/register', data={'name': 'Test', 'email': 't@t.com', 'password': 'pw12345',
                              'sq1': 'Q1', 'sa1': 'A', 'sq2': 'Q2', 'sa2': 'B', 'sq3': 'Q3', 'sa3': 'C'})
    assert 'Welcome back' in text(login(app.test_client(), 't@t.com', 'pw12345'))
    r = app.test_client()
    r.post('/recover', data={'email': 't@t.com'})
    assert 'question 2' in text(r.post('/recover/verify', data={'answer1': 'a', 'answer2': 'x', 'answer3': 'c'}))
    assert 'new_password' in text(r.post('/recover/verify', data={'answer1': 'a', 'answer2': 'b', 'answer3': 'c'}))
    r.post('/recover/reset', data={'new_password': 'newpw999'})
    assert 'Welcome back' in text(login(app.test_client(), 't@t.com', 'newpw999'))


def test_duplicate_email_rejected(client):
    r = client.post('/register', data={'name': 'X', 'email': 'bob@demo.com', 'password': 'x',
                                       'sq1': 'q', 'sa1': 'a', 'sq2': 'q', 'sa2': 'b', 'sq3': 'q', 'sa3': 'c'},
                    follow_redirects=True)
    assert 'already registered' in text(r)


# ── Booking rules ───────────────────────────────────────────────

def book(c, car, start, end):
    return text(c.post(f'/book/{car}', data={'start_date': start, 'end_date': end}, follow_redirects=True))


@pytest.mark.parametrize('start,end,message', [
    (D(-10), D(-5), 'cannot be in the past'),
    (D(400), D(405), 'only available'),
    (D(10), D(5), 'must be after'),
    ('abc', D(5), 'Invalid date'),
])
def test_invalid_bookings_rejected(make_client, start, end, message):
    assert message in book(make_client('bob@demo.com'), 1, start, end)


def test_cannot_rent_own_car(make_client):
    assert 'cannot rent your own car' in book(make_client('alice@demo.com'), 1, D(3), D(5))


def test_overlapping_booking_rejected(make_client):
    assert 'Booking request sent' in book(make_client('bob@demo.com'), 1, D(3), D(6))
    assert 'already booked' in book(make_client('carol@demo.com'), 1, D(4), D(8))


# ── Approve → pay → review (Mediator + Proxy) ────────────────────

@pytest.fixture
def paid_booking(make_client, db_conn):
    bob, alice = make_client('bob@demo.com'), make_client('alice@demo.com')
    book(bob, 1, D(3), D(6))
    bid = db_conn.execute('SELECT MAX(id) FROM bookings').fetchone()[0]
    alice.post(f'/booking/{bid}/approve')
    before = db_conn.execute("SELECT balance FROM users WHERE email='bob@demo.com'").fetchone()[0]
    assert 'processed' in text(bob.post(f'/pay/{bid}', follow_redirects=True))
    return bob, alice, bid, before


def test_payment_moves_money_and_logs(paid_booking, db_conn):
    _, _, bid, before = paid_booking
    after = db_conn.execute("SELECT balance FROM users WHERE email='bob@demo.com'").fetchone()[0]
    assert before - after == pytest.approx(195)  # 3 days x $65
    assert db_conn.execute('SELECT status FROM bookings WHERE id=?', (bid,)).fetchone()[0] == 'confirmed'
    assert db_conn.execute("SELECT status FROM payment_log WHERE booking_id=?", (bid,)).fetchone()[0] == 'success'


def test_paid_booking_cannot_be_cancelled_or_reapproved(paid_booking):
    bob, alice, bid, _ = paid_booking
    assert 'already been paid' in text(bob.post(f'/booking/{bid}/cancel', follow_redirects=True))
    assert 'Only pending' in text(alice.post(f'/booking/{bid}/approve', follow_redirects=True))


def test_booking_sends_messages(paid_booking, db_conn):
    assert db_conn.execute('SELECT COUNT(*) FROM messages').fetchone()[0] >= 3


def test_one_review_per_car(paid_booking, db_conn):
    bob = paid_booking[0]
    assert 'Rating must be' in text(bob.post('/review/1', data={'rating': '9'}, follow_redirects=True))
    assert 'Review submitted' in text(bob.post('/review/1', data={'rating': '5', 'comment': 'Great'}, follow_redirects=True))
    assert 'already reviewed' in text(bob.post('/review/1', data={'rating': '4'}, follow_redirects=True))
    assert db_conn.execute('SELECT COUNT(*) FROM reviews WHERE car_id=1').fetchone()[0] == 1


def test_review_requires_paid_rental(make_client):
    r = make_client('bob@demo.com').post('/review/1', data={'rating': '5'}, follow_redirects=True)
    assert 'confirmed (paid) rental' in text(r)


def test_non_owner_cannot_approve(make_client, db_conn):
    book(make_client('bob@demo.com'), 1, D(3), D(6))
    bid = db_conn.execute('SELECT MAX(id) FROM bookings').fetchone()[0]
    assert 'not found' in text(make_client('carol@demo.com').post(f'/booking/{bid}/approve', follow_redirects=True))


# ── Listings and watchlist (Builder + Observer) ──────────────────

def test_new_listing_appears_in_search(make_client):
    alice = make_client('alice@demo.com')
    r = alice.post('/cars/new', data={'make': 'Honda', 'model': 'Civic', 'year': '2022',
                                      'location': 'Detroit, MI', 'price_per_day': '45'}, follow_redirects=True)
    assert 'Car listed' in text(r)
    assert 'Honda Civic' in text(make_client('bob@demo.com').get('/search?location=Detroit'))


def test_price_drop_notifies_watcher(make_client, db_conn):
    make_client('bob@demo.com').post('/watch/2', data={'max_price': '70'})
    make_client('alice@demo.com').post('/cars/2/edit', data={'price_per_day': '60', 'is_available': '1'})
    n = db_conn.execute("SELECT COUNT(*) FROM notifications n JOIN users u ON u.id=n.user_id "
                        "WHERE u.email='bob@demo.com' AND event_type='price_drop'").fetchone()[0]
    assert n == 1


# ── Bad input never causes a server error ───────────────────────

@pytest.mark.parametrize('email,url,data', [
    ('alice@demo.com', '/booking/9999/approve', {}),
    ('alice@demo.com', '/cars/1/edit', {'price_per_day': 'abc'}),
    ('alice@demo.com', '/cars/new', {'make': 'X', 'model': 'Y', 'year': 'abc', 'location': 'Z', 'price_per_day': '1'}),
    ('bob@demo.com', '/watch/9999', {}),
    ('bob@demo.com', '/review/1', {'rating': 'abc'}),
    ('bob@demo.com', '/messages/send', {'receiver_id': 'abc', 'content': 'hi'}),
])
def test_bad_input_handled(make_client, email, url, data):
    assert make_client(email).post(url, data=data).status_code < 500


def test_message_send(make_client):
    r = make_client('bob@demo.com').post('/messages/send', data={'receiver_id': '1', 'content': 'hi'}, follow_redirects=True)
    assert 'Message sent' in text(r)
