from __future__ import absolute_import
import webtest.lint
import webtest
import os

os.environ['CLAY_CONFIG'] = 'config.json'

from clay import app, config
import clay.wsgi
log = config.get_logger('clay.tests.hello_world')


# Test application
@app.route('/', methods=['GET'])
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
