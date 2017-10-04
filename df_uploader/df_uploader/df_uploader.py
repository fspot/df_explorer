import logging
import tempfile
import os
from contextlib import suppress

import requests


def upload_df(df, df_id: str, host=None):
    logger = logging.getLogger('df_uploader')
    df_id = df_id.replace('/', '-')\
                 .replace(' ', '-')\
                 .lower()
    host = host or os.getenv('DF_EXPLORER_HOST')
    if host is None:
        raise Exception("Missing parameter: host")
    if not host.endswith('/'):
        host += '/'
    url = f"{host}df/{df_id}"

    with tempfile.NamedTemporaryFile() as f:
        tmp_file_name = f.name

    try:
        logger.info('Dump dataframe to feather file...')
        df.to_feather(tmp_file_name)
        logger.info('Send it by HTTP...')
        with open(tmp_file_name, 'rb') as f:
            requests.post(url, data=f)
        logger.info(f'Done! Dataframe will be accessible at url {url}')
    finally:
        with suppress(FileNotFoundError):
            os.unlink(tmp_file_name)
