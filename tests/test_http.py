from __future__ import absolute_import, unicode_literals

from http.client import HTTPSConnection
import mock
import clay.config
from clay import http
try:
    from urllib.request import Request as urllib_Request
    from urllib.request import HTTPSHandler, urlopen
    from urllib.error import HTTPError, URLError
except ImportError:
    from urllib2 import urlopen, install_opener, build_opener, HTTPError, HTTPSHandler, URLError
import tempfile
import shutil
import os.path

from unittest import TestCase

s = mock.sentinel


class RequestTestCase(TestCase):
    def test_method_with_method(self):
        req = http.Request(url='http://www.uber.com', method=s.method)
        self.assertEqual(req.get_method(), s.method)

    def test_method_no_data(self):
        req = http.Request(url='http://www.uber.com', data=None)
        self.assertEqual(req.get_method(), 'GET')

    def test_method_data(self):
        req = http.Request(url='http://www.uber.com', data={'1': 2})
        self.assertEqual(req.get_method(), 'POST')


@mock.patch('ssl.get_server_certificate')
@mock.patch('clay.http.urlopen')
class LittleRequestTestCase(TestCase):
    def test_error_returns_response(self, mock_urlopen, mock_get_cert):
        e = HTTPError('http://www.google.com', 404, 'Some message', {}, None)
        mock_urlopen.side_effect = e
        response = http.request('GET', 'http://www.google.com')
        self.assertEqual(response, http.Response(status=404, headers={}, data=None))

    def test_http_only(self, mock_urlopen, mock_get_cert):
        self.assertRaises(URLError, http.request, 'GET', 'ftp://google.com')

    def test_good(self, mock_urlopen, mock_get_cert):
        mock_response = mock.Mock(name='resp')
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = s.body
        mock_response.headers = {}
        mock_urlopen.return_value = mock_response
        response = http.request('GET', 'http://www.google.com')
        self.assertEqual(response, http.Response(status=200, headers={}, data=s.body))

    def test_timeout_passed(self, mock_urlopen, mock_get_cert):
        http.request('GET', 'http://www.google.com', timeout=10)
        mock_urlopen.assert_called_once_with(mock.ANY, timeout=10)


def create_mock_http_connection():
    mock_conn = mock.MagicMock(name='https_connection')
    mock_resp = mock.MagicMock(name='https_response')
    mock_resp.read.return_value = ''
    mock_resp.recv.return_value = ''
    mock_resp.status = 200
    # In PY3 variable changed to code instead of status
    mock_resp.code = 200
    mock_resp.reason = 'A OK'
    mock_conn.getresponse.return_value = mock_resp
    conn = mock.MagicMock(spec=HTTPSConnection, return_value=mock_conn)
    return conn


@mock.patch('http.client.HTTPSConnection', new_callable=create_mock_http_connection)
@mock.patch('ssl.get_server_certificate')
class SSLTestCase(TestCase):
    def setUp(self, *args, **kwargs):
        self.wd = tempfile.mkdtemp()
        with open(os.path.join(self.wd, 'ca.crt'), 'w') as fd:
            fd.write('')

    def tearDown(self, *args, **kwargs):
        if self.wd is not None and os.path.exists(self.wd):
            shutil.rmtree(self.wd)

    def test_ssl_checks_if_enabled(self, mock_get_cert, mock_conn):
        config_dict = {
            'http': {
                'ca_certs_file': os.path.join(self.wd, 'ca.crt'),
                'verify_server_certificates': True,
            }
        }
        with mock.patch.dict(clay.config.CONFIG.config, config_dict):
            http.request('GET', 'https://www.google.com')
            mock_get_cert.assert_called_once_with(('www.google.com', 443), ca_certs=os.path.join(self.wd, 'ca.crt'))

    def test_ssl_checks_not_enabled(self, mock_get_cert, mock_conn):
        config_dict = {
            'http': {
                'ca_certs_file': os.path.join(self.wd, 'ca.crt'),
                'verify_server_certificates': False,
            }
        }
        with mock.patch.dict(clay.config.CONFIG.config, config_dict):
            http.request('GET', 'https://www.google.com')
            self.assertEqual(mock_get_cert.call_count, 0)

    def test_ssl_certs_disabled_if_no_file(self, mock_get_cert, mock_conn):
        config_dict = {
            'http': {
                'ca_certs_file': os.path.join(self.wd, 'does_not_exist.crt'),
                'verify_server_certificates': True,
            }
        }
        with mock.patch.dict(clay.config.CONFIG.config, config_dict):
            http.request('GET', 'https://www.google.com')
            self.assertEqual(mock_get_cert.call_count, 0)

    def test_ssl_checks_honored(self, mock_get_cert, mock_conn):
        config_dict = {
            'http': {
                'ca_certs_file': os.path.join(self.wd, 'ca.crt'),
                'verify_server_certificates': True,
            }
        }
        mock_get_cert.side_effect = ValueError('Invalid SSL certificate')
        with mock.patch.dict(clay.config.CONFIG.config, config_dict):
            self.assertRaises(ValueError, http.request, 'GET', 'https://www.google.com')
            mock_get_cert.assert_called_once_with(('www.google.com', 443), ca_certs=os.path.join(self.wd, 'ca.crt'))
