"""Unit tests for the six design pattern classes, independent of HTTP routes."""
import pytest

import app as A


def test_singleton_returns_same_instance():
    assert A.UserSession() is A.UserSession.get_instance()


def test_builder_builds_listing():
    listing = (A.ConcreteCarBuilder(owner_id=1)
               .set_basic_info('Honda', 'Civic', '2022')
               .set_mileage('1000').set_location('Detroit, MI')
               .set_price('45').build())
    assert listing['make'] == 'Honda' and listing['year'] == 2022
    assert listing['price_per_day'] == 45.0 and listing['mileage'] == 1000


def test_builder_rejects_missing_field():
    with pytest.raises(ValueError, match='location'):
        A.ConcreteCarBuilder(1).set_basic_info('Honda', 'Civic', 2022).set_price(45).build()


def test_observer_notifies_every_attached_observer():
    received = []

    class Recorder(A.RenterObserver):
        def notify(self, car_id, event_type, message):
            received.append((car_id, event_type))

    subject = A.CarListingSubject(car_id=7)
    subject.attach(Recorder()); subject.attach(Recorder())
    subject.notify_observers('price_drop', 'cheaper')
    assert received == [(7, 'price_drop'), (7, 'price_drop')]


def _user_with_answers(a1, a2, a3):
    h = A.hash_password
    return {'security_answer1': h(a1), 'security_answer2': h(a2), 'security_answer3': h(a3)}


def test_chain_passes_when_all_answers_correct():
    user = _user_with_answers('rex', 'detroit', 'jones')
    result = A.build_recovery_chain().handle(user, {'answer1': 'Rex', 'answer2': 'detroit ', 'answer3': 'JONES'})
    assert result['success']


@pytest.mark.parametrize('wrong', ['answer1', 'answer2', 'answer3'])
def test_chain_stops_at_first_wrong_answer(wrong):
    user = _user_with_answers('rex', 'detroit', 'jones')
    answers = {'answer1': 'rex', 'answer2': 'detroit', 'answer3': 'jones', wrong: 'nope'}
    result = A.build_recovery_chain().handle(user, answers)
    assert not result['success'] and f'question {wrong[-1]}' in result['message']


def test_hash_is_salted_and_verifiable():
    h1, h2 = A.hash_password('secret'), A.hash_password('secret')
    assert h1 != h2
    assert A.verify_secret(h1, 'secret') and not A.verify_secret(h1, 'wrong')


def test_verify_accepts_legacy_sha256():
    import hashlib
    legacy = hashlib.sha256(b'secret').hexdigest()
    assert A.verify_secret(legacy, 'secret') and not A.verify_secret(legacy, 'nope')


def test_parse_date():
    assert A.parse_date('2026-01-31').day == 31
    assert A.parse_date('bad') is None and A.parse_date(None) is None
