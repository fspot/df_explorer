import logging
import tempfile
import inspect
import io
import os
from contextlib import suppress

import requests
import joblib


def to_pickled_dict(d):
    def as_picklable(obj):
        try:
            f = io.BytesIO()
            joblib.dump(obj, f)
        except Exception:
            return None
        else:
            f.seek(0)
            return f.read()

    return {k: as_picklable(v) for k, v in d.items()}


def to_serializable_traceback(exc_type, exc_value, tb):
    frame = tb.tb_frame
    filename = inspect.getsourcefile(tb) or inspect.getfile(tb) or '<unknown>'
    sourcecode = frame.f_globals['__loader__'].get_source(frame.f_globals['__name__'])
    serializable_tb = dict(
        filename=filename,
        sourcecode=sourcecode,
        tb_next=None,
        tb_lineno=tb.tb_lineno,
        tb_frame=dict(
            f_code=dict(co_name=frame.f_code.co_name),
            f_locals=to_pickled_dict(frame.f_locals),
            f_globals=to_pickled_dict(frame.f_globals),
        )
    )
    return {
        'exc_type': exc_type,
        'exc_value': exc_value,
        'tb': serializable_tb,
    }


def upload_tb(tb, tb_id: str, host=None):
    logger = logging.getLogger('tb_uploader')
    tb_id = tb_id.replace('/', '-')\
                 .replace(' ', '-')\
                 .lower()
    host = host or os.getenv('TB_EXPLORER_HOST')
    if host is None:
        raise Exception("Missing parameter: host")
    if not host.endswith('/'):
        host += '/'
    url = f"{host}tb/{tb_id}"

    with tempfile.NamedTemporaryFile() as f:
        tmp_file_name = f.name

    try:
        logger.info('Dumping traceback...')
        joblib.dump(tb, tmp_file_name)
        logger.info('Send it by HTTP...')
        with open(tmp_file_name, 'rb') as f:
            requests.post(url, data=f)
        logger.info(f'Done! Traceback will be accessible at url {url}')
    finally:
        with suppress(FileNotFoundError):
            os.unlink(tmp_file_name)


def foo(x):
    y = x * 2
    z = 1 / (y - 2 * x)  # oops
    return x, y, z


def main():
    try:
        foo(42)
    except Exception:
        import sys
        exc_type, exc_value, tb = sys.exc_info()
        tb = tb.tb_next
        import ipdb; ipdb.set_trace()
        stb = to_serializable_traceback(exc_type, exc_value, tb)
        upload_tb(stb, 'test')


if __name__ == '__main__':
    main()
