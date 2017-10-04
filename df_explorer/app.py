"""DataFrame explorer

Usage:
  app.py [--storage STORAGE] [--port PORT]
  app.py -h | --help

Optional arguments:
  -h, --help         Show this help message and exit
  --port PORT        TCP port number [default: 5000]
  --storage STORAGE  Path of the data storing folder [default: ./store]

"""

import os
import datetime
from contextlib import suppress
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, request, render_template
from docopt import docopt

import debugger


def create_app(storage_dir):
    app = Flask(__name__)

    @app.route('/df/<df_id>', methods=['GET'])
    def df_view(df_id):
        df_file = storage_dir / (str(df_id) + '.dump')
        if df_file.exists():
            df = pd.read_feather(str(df_file))
            return debugger.launch_debugger(df)
        else:
            print(f"[err] No file {df_file}")
            return jsonify({"success": False, "error": f"no DF with id {df_id}"})

    @app.route('/df/<df_id>', methods=['POST'])
    def df_upload(df_id):
        try:
            df_file = storage_dir / (str(df_id) + '.dump')
            with open(df_file, 'wb') as f:
                while not request.stream.is_exhausted:
                    f.write(request.stream.read(1024 * 100))
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
        else:
            return jsonify({'success': True, 'message': 'File uploaded'})

    @app.route('/')
    def home():
        def pretty_size(nb_bytes):
            if nb_bytes < 150:
                return f"{nb_bytes} bytes"
            elif nb_bytes < 1024 * 200:
                nb_kB = nb_bytes / 1024.
                return f"{nb_kB:.2f} kB"
            elif nb_bytes < (1024 ** 2) * 200:
                nb_MB = nb_bytes / (1024. ** 2)
                return f"{nb_MB:.2f} MB"
            else:
                nb_GB = nb_bytes / (1024. ** 3)
                return f"{nb_GB:.2f} GB"

        files = [
            {
                "name": file.name[:-5],
                "mtime": datetime.datetime.fromtimestamp(
                    file.lstat().st_mtime
                ).strftime("%Y-%m-%d %H:%M"),
                "size": pretty_size(file.lstat().st_size),
            }
            for file in storage_dir.glob('*.dump')
        ]
        files = sorted(files, key=lambda e: e['mtime'], reverse=True)
        return render_template('index.html', files=files)

    return app


def main():
    os.environ['WERKZEUG_DEBUG_PIN'] = 'off'
    args = docopt(__doc__)

    storage_dir = Path(args['--storage']).resolve()
    print(f'[info] storage dir: {storage_dir}')
    with suppress(FileExistsError):
        storage_dir.mkdir()

    app = create_app(storage_dir)
    app.run(
        host='localhost',
        port=int(args['--port']),
        debug=True,
        use_reloader=False,
        threaded=True,
    )


if __name__ == '__main__':
    main()
