from __future__ import absolute_import

from collections import namedtuple
import urllib2

from clay import config


Response = namedtuple('Response', ('status', 'headers', 'data'))
log = config.get_logger('clay.http')


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
	Convenience wrapper around urllib2
	'''
	req = Request(uri, headers=headers, data=data, method=method)
	if not req.get_type() in ('http', 'https'):
		raise urllib2.URLError('Only http and https protocols are supported')

	try:
		resp = urllib2.urlopen(req)
		resp = Response(
			status=resp.getcode(),
			headers=resp.headers,
			data=resp.read())
		log.debug('%i %s %s' % (resp.status, method, uri))
	except urllib2.HTTPError, e:
		resp = Response(
			status=e.getcode(),
			headers=e.headers,
			data=e.read())
		log.warning('%i %s %s' % (resp.status, method, uri))

	return resp
