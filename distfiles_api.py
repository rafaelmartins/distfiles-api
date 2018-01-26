# coding: utf-8

from flask import Flask, abort, request
import hashlib
import os
import re

app = Flask(__name__)

app.config.update(
    AUTH_TOKEN='bola',
    DISTFILES_BASEDIR=os.getcwd(),
)
app.config.from_envvar('DISTFILES_CONFIG', True)

re_sha512 = re.compile(r'([0-9a-f]{128}) (\*| )(.+)')


@app.route('/', methods=['POST'])
def upload():
    if request.authorization is None:
        abort(401)
    if request.authorization.username != app.config['AUTH_TOKEN']:
        abort(401)

    if 'file' not in request.files:
        abort(400)
    if any(i not in request.form for i in ('project', 'sha512')):
        abort(400)

    match_sha512 = re_sha512.match(request.form['sha512'])
    if match_sha512 is None:
        abort(400)

    f = request.files['file']

    if len(f.filename) < 4:
        abort(400)
    if any(i in f.filename for i in '/\\'):
        abort(400)

    # this should waste some memory, but it is ok. also, upload file size
    # should be restricted in nginx.
    data = f.read()

    if match_sha512.group(1) != hashlib.sha512(data).hexdigest():
        abort(400)

    destdir = os.path.join(app.config['DISTFILES_BASEDIR'],
                           request.form['project'])
    dest = os.path.join(destdir, f.filename)
    dest_sha512 = '%s.sha512' % dest

    if not os.path.isdir(destdir):
        os.makedirs(destdir)

    with open(dest_sha512, 'w') as fp:
        fp.write(request.form['sha512'])

    with open(dest, 'w') as fp:
        fp.write(data)

    return 'OK\n'
