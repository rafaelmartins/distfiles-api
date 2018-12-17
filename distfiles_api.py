# coding: utf-8

import hashlib
import os
import re
import shutil
import tarfile
import tempfile

from flask import Flask, request, Blueprint, current_app
from prettyconf import config

blueprint = Blueprint('main', __name__)
re_sha512 = re.compile(r'([0-9a-f]{128}) (\*| )(.+)')
CHUNK_SIZE = 8192

UMASK = os.umask(0)
os.umask(UMASK)


def create_app():
    app = Flask(__name__)

    app.config.update(
        AUTH_TOKENS=config('AUTH_TOKENS', config.list, default=['token']),
        DISTFILES_BASEDIR=config('DISTFILES_BASEDIR', default=os.getcwd()),
    )
    app.config.from_envvar('DISTFILES_CONFIG', True)
    app.register_blueprint(blueprint)
    return app


def abort(code, content):
    return content, code, {'Content-Type': 'text/plain'}


@blueprint.route('/', methods=['POST'])
def upload():
    if request.authorization is None:
        return abort(401, 'NOAUTH')
    if request.authorization.username not in current_app.config['AUTH_TOKENS']:
        return abort(401, 'BADAUTH')

    if 'file' not in request.files:
        return abort(400, 'NOFILE')
    if any(i not in request.form for i in ('project', 'version', 'sha512')):
        return abort(400, 'BADFORM')

    match_sha512 = re_sha512.match(request.form['sha512'])
    if match_sha512 is None:
        return abort(400, 'BADFORM_SHA512')

    hash_sha512, binary_flag, filename = match_sha512.groups()

    if len(filename) < 4:
        return abort(400, 'BADFILENAME_LENGTH')
    if any(i in filename for i in '/\\'):
        return abort(400, 'BADFILENAME_SLASH')

    fileobj = request.files['file']

    if filename != fileobj.filename:
        return abort(400, 'BADSHA512_FILENAME')

    temporary_file = tempfile.NamedTemporaryFile(delete=False)
    calculated_hash = hashlib.sha512()
    while True:
        try:
            chunk = fileobj.read(CHUNK_SIZE)
        except IOError:
            os.unlink(temporary_file.name)
            raise
        if not chunk:
            break
        calculated_hash.update(chunk)
        temporary_file.write(chunk)

    if hash_sha512 != calculated_hash.hexdigest():
        os.unlink(temporary_file.name)
        return abort(400, 'BADSHA512_HASH')

    p = '%s-%s' % (request.form['project'], request.form['version'])
    destdir = os.path.join(current_app.config['DISTFILES_BASEDIR'],
                           request.form['project'], p)
    dest = os.path.join(destdir, filename)
    dest_sha512 = '%s.sha512' % dest

    if not os.path.isdir(destdir):
        os.makedirs(destdir)

    with open(dest_sha512, 'w') as fp:
        fp.write(request.form['sha512'])
        fp.flush()
        os.fdatasync(fp)

    temporary_file.flush()
    os.fdatasync(temporary_file)
    temporary_file.close()

    shutil.move(temporary_file.name, dest)
    os.chmod(dest, 0o666 & ~UMASK)

    latest = os.path.join(current_app.config['DISTFILES_BASEDIR'],
                          request.form['project'], 'LATEST')
    if os.path.lexists(latest):
        os.remove(latest)

    os.symlink(p, latest)

    if request.form.get('extract', '').lower() in ('1', 'true'):
        try:
            with tarfile.open(dest, 'r:*') as fp:
                fp.extractall(destdir)
        except tarfile.ReadError:
            return abort(400, 'BAD_TAR_FILE')

    return abort(200, 'OK')


@blueprint.route('/health')
def health():
    return 'OK'
