from __future__ import absolute_import

import contextlib
from collections import namedtuple
import httplib
import urllib2
import urlparse
import os.path
import ssl

from clay import config


Response = namedtuple('Response', ('status', 'headers', 'data'))
log = config.get_logger('clay.http')

DEFAULT_CA_CERTS = '/etc/ssl/certs/ca-certificates.crt'


class VerifiedHTTPSOpener(urllib2.HTTPSHandler):
    def https_open(self, req):
        ca_certs = config.get('http.ca_certs_file', DEFAULT_CA_CERTS)
        if config.get('http.verify_server_certificates', True) and os.path.exists(ca_certs):
            frags = urlparse.urlparse(req.get_full_url())
            ssl.get_server_certificate((frags.hostname, frags.port or 443),
                ca_certs=ca_certs)
        return self.do_open(httplib.HTTPSConnection, req)

urllib2.install_opener(urllib2.build_opener(VerifiedHTTPSOpener))


class Request(urllib2.Request):
    '''
    This subclass adds "method" to urllib2.Request
    '''
    def __init__(self, url, data=None, headers={}, origin_req_host=None,
                 unverifiable=False, method=None):
        urllib2.Request.__init__(self, url, data, headers, origin_req_host,
                                 unverifiable)
        if headers is None:
            self.headers = {}
        self.method = method

    def get_method(self):
        if self.method is not None:
            return self.method
        if self.has_data():
            return 'POST'
        else:
            return 'GET'


def request(method, uri, headers={}, data=None):
    '''
    Convenience wrapper around urllib2. Returns a Response namedtuple with 'status', 'headers', and 'data' fields
    '''
    req = Request(uri, headers=headers, data=data, method=method)
    if not req.get_type() in ('http', 'https'):
        raise urllib2.URLError('Only http and https protocols are supported')

    try:
        with contextlib.closing(urllib2.urlopen(req)) as resp:
            resp = Response(
                status=resp.getcode(),
                headers=resp.headers,
                data=resp.read())
            log.debug('%i %s %s' % (resp.status, method, uri))
    except urllib2.HTTPError, e:
        # if there was a connection error, the underlying fd might be None and we can't read it
        if e.fp is not None:
            resp = Response(
                status=e.getcode(),
                headers=e.hdrs,
                data=e.read())
        else:
            resp = Response(
                status=e.getcode(),
                headers=e.hdrs,
                data=None)
        log.warning('%i %s %s' % (resp.status, method, uri))

    return resp
