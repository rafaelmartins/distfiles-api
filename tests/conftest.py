import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from flask import Flask, url_for

parent_path: Path = Path(__file__).parent.parent.resolve()
sys.path.append(parent_path.as_posix())


@pytest.yield_fixture()
def app():
    temporary_directory = TemporaryDirectory()
    os.environ['DISTFILES_BASEDIR'] = temporary_directory.name
    from distfiles_api import create_app
    app_ = create_app()
    app_.config.update(SERVER_NAME='localhost')
    ctx = app_.app_context()
    ctx.push()
    yield app_
    ctx.pop()


@pytest.fixture()
def test_client(app: Flask):
    return app.test_client()


@pytest.fixture()
def upload_url(app: Flask):
    assert app
    return url_for('main.upload')

