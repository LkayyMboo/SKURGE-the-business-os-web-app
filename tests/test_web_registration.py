from types import SimpleNamespace
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import web_app


@pytest.fixture
def client():
    app = web_app.create_app({"TESTING": True, "WTF_CSRF_ENABLED": False, "RATELIMIT_ENABLED": False, "SECRET_KEY": "test-only-secret"})
    return app.test_client()


def test_owner_registration_collects_business_details_on_same_page(client):
    response = client.get('/register')
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'Create account &amp; workspace' in body or 'Create account & workspace' in body
    assert 'name="business_name"' in body
    assert 'name="business_type"' in body
    assert 'name="industry"' in body
    assert 'name="province"' in body


def test_owner_registration_creates_business_and_redirects_to_dashboard(client, monkeypatch):
    user = SimpleNamespace(id='user-test', full_name='Test Owner', email='owner@example.com')
    created = {}
    monkeypatch.setattr(web_app.AuthService, 'register', lambda *args: user)
    monkeypatch.setattr(web_app.BusinessService, 'create_business', lambda **kwargs: created.update(kwargs) or SimpleNamespace(name=kwargs['name']))
    response = client.post('/register', data={
        'full_name': 'Test Owner', 'email': 'owner@example.com', 'password': 'LongEnoughPass123',
        'business_name': 'Test Studio', 'business_type': 'Sole Proprietor', 'industry': 'Technology',
        'province': 'Mpumalanga', 'city': 'Nelspruit', 'business_email': 'studio@example.com',
        'business_phone': '0123456789', 'registration_status': 'draft', 'referral_code': '',
    })
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/app/dashboard')
    assert created['owner_user_id'] == 'user-test'
    assert created['name'] == 'Test Studio'
    assert created['province'] == 'Mpumalanga'
    with client.session_transaction() as sess:
        assert sess['user']['id'] == 'user-test'
        assert sess.permanent is True


def test_owner_registration_requires_business_fields_before_creating_account(client, monkeypatch):
    called = {'register': False}
    monkeypatch.setattr(web_app.AuthService, 'register', lambda *args: called.update(register=True))
    response = client.post('/register', data={
        'full_name': 'Test Owner', 'email': 'owner@example.com', 'password': 'LongEnoughPass123',
        'business_name': '', 'business_type': '', 'industry': '', 'province': '', 'referral_code': '',
    })
    assert response.status_code == 200
    assert called['register'] is False
    assert 'Complete the business name, type, industry and province' in response.get_data(as_text=True)
