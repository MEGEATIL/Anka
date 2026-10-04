"""Kamera girişindeki kaba kuvvet sınırlamasını donanım gerektirmeden doğrular."""

import pytest


pytest.importorskip("flask")
import kameraserver


def test_camera_login_blocks_after_maximum_failed_attempts():
    kameraserver.SIFRE = "test-password"
    kameraserver.failed_attempts.clear()
    client = kameraserver.app.test_client()

    for _ in range(kameraserver.MAX_FAIL):
        response = client.post('/giris', data={'sifre': 'yanlis'})

    assert response.status_code == 200
    assert 'bloke' in response.get_data(as_text=True).lower()
    assert kameraserver.is_blocked('127.0.0.1')


def test_camera_does_not_trust_forwarded_ip_without_proxy_configuration():
    kameraserver.app.config['TRUST_PROXY'] = False
    with kameraserver.app.test_request_context(
        '/',
        headers={'X-Forwarded-For': '203.0.113.50'},
        environ_base={'REMOTE_ADDR': '127.0.0.8'},
    ):
        assert kameraserver.get_client_ip() == '127.0.0.8'


def test_camera_sensitive_endpoints_require_an_authenticated_session():
    kameraserver.SIFRE = "test-password"
    client = kameraserver.app.test_client()

    for endpoint in ('/url', '/enroll?name=Ada', '/face_login'):
        response = client.get(endpoint)
        assert response.status_code == 302
        assert '/giris' in response.headers['Location']
