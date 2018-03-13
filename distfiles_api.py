# coding: utf-8

from flask import Flask, request
import hashlib
import os
import re
import tarfile

app = Flask(__name__)

app.config.update(
    AUTH_TOKEN='token',
    DISTFILES_BASEDIR=os.getcwd(),
)
app.config.from_envvar('DISTFILES_CONFIG', True)

re_sha512 = re.compile(r'([0-9a-f]{128}) (\*| )(.+)')


def abort400():
    return 'BAD_REQUEST\n', 400, {'Content-Type': 'text/plain'}


def abort401():
    return 'UNAUTHORIZED\n', 401, {'Content-Type': 'text/plain'}


@app.route('/', methods=['POST'])
def upload():
    if request.authorization is None:
        return abort401()
    if request.authorization.username != app.config['AUTH_TOKEN']:
        return abort401()

    if 'file' not in request.files:
        return abort400()
    if any(i not in request.form for i in ('project', 'version', 'sha512')):
        return abort400()

    match_sha512 = re_sha512.match(request.form['sha512'])
    if match_sha512 is None:
        return abort400()

    hash_sha512, binary_flag, filename = match_sha512.groups()

    if len(filename) < 4:
        return abort400()
    if any(i in filename for i in '/\\'):
        return abort400()

    fileobj = request.files['file']

    if filename != fileobj.filename:
        return abort400()

    # this should waste some memory, but it is ok. also, upload file size
    # should be already restricted by nginx.
    data = fileobj.read()

    if hash_sha512 != hashlib.sha512(data).hexdigest():
        return abort400()

    p = '%s-%s' % (request.form['project'], request.form['version'])
    destdir = os.path.join(app.config['DISTFILES_BASEDIR'],
                           request.form['project'], p)
    dest = os.path.join(destdir, filename)
    dest_sha512 = '%s.sha512' % dest

    if not os.path.isdir(destdir):
        os.makedirs(destdir)

    with open(dest_sha512, 'w') as fp:
        fp.write(request.form['sha512'])

    with open(dest, 'wb') as fp:
        fp.write(data)

    latest = os.path.join(app.config['DISTFILES_BASEDIR'],
                          request.form['project'], 'LATEST')
    if os.path.lexists(latest):
        os.remove(latest)

    os.symlink(p, latest)

    if 'extract' in request.form and \
       request.form['extract'].lower() in ('1', 'true'):
        with tarfile.open(dest, 'r:*') as fp:
            fp.extractall(destdir)

    return 'OK\n', 200, {'Content-Type': 'text/plain'}
