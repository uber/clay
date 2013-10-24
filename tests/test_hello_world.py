from __future__ import absolute_import
import webtest.lint
import webtest
import os

os.environ['CLAY_CONFIG'] = 'config.json'

from clay import app, config, http
import clay.wsgi
log = config.get_logger('clay.tests.hello_world')


# Test application
@app.route('/', methods=['GET'])
@http.cache_control(max_age=3600, public=True, no_cache="Cookies")
def hello_world():
    return 'Hello, world!'


# Test methods
app = clay.wsgi.application
app = webtest.lint.middleware(app)
app = webtest.TestApp(app)


def test_hello_world():
    res = app.get('/')
    assert res.status_int == 200
    assert res.body == 'Hello, world!'

def test_cache_control():
    res = app.get('/')
    assert res.headers['Cache-Control'] == 'max-age=3600, public, no-cache="Cookies"'
