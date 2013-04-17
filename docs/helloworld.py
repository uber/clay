# This is a minimalist example of a clay view. Run it like so:
#
#   CLAY_CONFIG=simple-clay.conf clay-devserver
#
from __future__ import absolute_import
from clay import app


@app.route('/', methods=['GET'])
def hello():
    return 'Hello World!'
