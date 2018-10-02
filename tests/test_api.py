import base64
from io import BytesIO
from pathlib import Path

from flask import Response
from flask.testing import FlaskClient

FILE_NAME = 'test-file.txt'
FILE_DATA = b'0' * 1024 * 64
FILE_HASH = (
    '5b42c8db4346cf5fdcb8a2299fdc557b336b8e599a'
    '31ff0f13089742bf83b27ad358c94f255a716230c35'
    'eed1bc390b95e3bb07b3c545f0c42269da84a104a07'
)


def build_headers(username, password=''):
    auth_data = f'{username}:{password}'.encode()
    return {
        'Authorization': f'Basic {base64.b64encode(auth_data).decode()}'
    }


def build_post_args(filename='a-file', **kwargs):
    return {
        'headers': VALID_TOKEN_HEADER,
        'data': {
            'file': (BytesIO(FILE_DATA), filename),
            **kwargs
        }
    }


VALID_TOKEN_HEADER = build_headers('token')


def test_no_auth(test_client: FlaskClient, upload_url):
    response: Response = test_client.post(upload_url)
    assert response.status_code == 401
    assert response.data == b'NOAUTH'


def test_bad_auth(test_client: FlaskClient, upload_url):
    response: Response = test_client.post(upload_url, headers=build_headers('wtfbbq'))
    assert response.status_code == 401
    assert response.data == b'BADAUTH'


def test_no_file(test_client: FlaskClient, upload_url):
    response: Response = test_client.post(upload_url, headers=VALID_TOKEN_HEADER)
    assert response.status_code == 400
    assert response.data == b'NOFILE'


def test_bad_form(test_client: FlaskClient, upload_url):
    response: Response = test_client.post(upload_url, **build_post_args())
    assert response.status_code == 400
    assert response.data == b'BADFORM'


def test_bad_form_sha_512(test_client: FlaskClient, upload_url):
    response: Response = test_client.post(upload_url, **build_post_args(project='abc', version='1.0', sha512='123'))
    assert response.status_code == 400
    assert response.data == b'BADFORM_SHA512'


def test_bad_filename_length(test_client: FlaskClient, upload_url):
    response: Response = test_client.post(upload_url, **build_post_args(project='abc', version='1.0',
                                                                        sha512=f'{FILE_HASH}  abc'))
    assert response.status_code == 400
    assert response.data == b'BADFILENAME_LENGTH'


def test_bad_filename_slash(test_client: FlaskClient, upload_url):
    response: Response = test_client.post(upload_url, **build_post_args(project='abc', version='1.0',
                                                                        sha512=f'{FILE_HASH}  abc/'))
    assert response.status_code == 400
    assert response.data == b'BADFILENAME_SLASH'


def test_bad_filename_backslash(test_client: FlaskClient, upload_url):
    response: Response = test_client.post(upload_url, **build_post_args(project='abc', version='1.0',
                                                                        sha512=f'{FILE_HASH}  abc\\'))
    assert response.status_code == 400
    assert response.data == b'BADFILENAME_SLASH'


def test_bad_filename(test_client: FlaskClient, upload_url):
    response: Response = test_client.post(upload_url, **build_post_args(project='abc', version='1.0',
                                                                        sha512=f'{FILE_HASH}  abcwd'))
    assert response.status_code == 400
    assert response.data == b'BADSHA512_FILENAME'


def test_bad_calculated_hash(test_client: FlaskClient, upload_url):
    wrong_hash = FILE_HASH[:-1] + '0'
    response: Response = test_client.post(upload_url, **build_post_args(project='abc', version='1.0',
                                                                        sha512=f'{wrong_hash}  a-file'))
    assert response.status_code == 400
    assert response.data == b'BADSHA512_HASH'


def test_ok(test_client: FlaskClient, upload_url):
    response: Response = test_client.post(upload_url, **build_post_args(project='abc', version='1.0',
                                                                        sha512=f'{FILE_HASH}  a-file'))
    assert response.status_code == 200
    assert response.data == b'OK'

    temporary_directory = Path(test_client.application.config['DISTFILES_BASEDIR'])
    project_folder = temporary_directory / 'abc'
    assert project_folder.exists()

    versioned_folder = project_folder / 'abc-1.0'
    assert versioned_folder.exists()

    latest_folder = project_folder / 'LATEST'
    assert latest_folder.is_symlink()
    assert latest_folder.resolve().samefile(versioned_folder)

    files = sorted([p.name for p in versioned_folder.iterdir()])
    assert files == ['a-file', 'a-file.sha512']

    assert (versioned_folder / 'a-file').read_bytes() == FILE_DATA
    assert (versioned_folder / 'a-file.sha512').read_text() == f'{FILE_HASH}  a-file'


def test_double_upload(test_client: FlaskClient, upload_url):
    def run():
        response: Response = test_client.post(upload_url, **build_post_args(project='abc', version='1.0',
                                                                            sha512=f'{FILE_HASH}  a-file'))
        assert response.status_code == 200
        assert response.data == b'OK'

    run()
    run()


def test_extract_bad_tar(test_client: FlaskClient, upload_url):
    response: Response = test_client.post(upload_url, **build_post_args(project='abc', version='1.0',
                                                                        sha512=f'{FILE_HASH}  a-file',
                                                                        extract='1'))
    assert response.status_code == 400
    assert response.data == b'BAD_TAR_FILE'
