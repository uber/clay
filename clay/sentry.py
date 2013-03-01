from __future__ import absolute_import

import raven.utils.wsgi
import raven

from clay import config

log = config.get_logger('clay.sentry')
client = None


def get_sentry_client():
    global client
    if client:
        return client
    dsn = config.get('sentry.url', None)
    if not dsn:
        return
    client = raven.Client(dsn=dsn)
    return client


def exception(exc_info, request=None, event_id=None, **extra):
    try:
        _exception(exc_info, request=request, event_id=event_id, **extra)
    except:
        log.exception('Unable to send event to sentry')


def _exception(exc_info, request=None, event_id=None, **extra):
    client = get_sentry_client()
    if not client:
        # return silently if sentry isn't configured
        return
    if request is not None:
        environ = request.environ
        client.capture('Exception', data={
            'sentry.interfaces.Http': {
                'method': request.method,
                'url': request.base_url,
                'data': request.data,
                'query_string': environ.get('QUERY_STRING', ''),
                'headers': dict(raven.utils.wsgi.get_headers(environ)),
                'env': dict(raven.utils.wsgi.get_environ(environ)),
            },
            'logger': extra.get("logger", "sentry"),
        }, extra=extra, exc_info=exc_info, event_id=event_id)
    else:
        client.captureException(exc_info, extra=extra,
            event_id=event_id)
