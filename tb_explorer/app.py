"""Traceback explorer

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
import gc
from contextlib import suppress
from pathlib import Path

import joblib
import psutil
import pandas as pd
from flask import Flask, jsonify, request, render_template, redirect, url_for
from werkzeug.debug.tbtools import Traceback, Frame
from werkzeug.debug import DebuggedApplication
from docopt import docopt

from .utils import from_serializable_traceback, pretty_size
from . import werk


werk.monkey_patch_debugged_application(DebuggedApplication)
werk.monkey_patch_flask_run(Flask)
werk.monkey_patch_traceback(Traceback)
werk.monkey_patch_frame(Frame)


def get_current_sessions(app):
    sessions = []
    for tb_num, (tb, tb_id, tb_date) in app.tb_sessions.items():
        sessions.append({
            "tb_num": tb_num,
            "tb": tb,
            "tb_id": tb_id,
            "tb_date": tb_date.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return sessions


def create_app(storage_dir):
    app = Flask(__name__)
    app.tb_sessions = {}

    def render_traceback(tb):
        return tb.render_full(
            evalex=True,
            evalex_trusted=True,
            secret=app.debugged_application.secret
        ).encode('utf-8', 'replace')

    @app.route('/tb/<tb_id>', methods=['GET'])
    def tb_new_session(tb_id):
        flask_app = app
        tb_file = storage_dir / (str(tb_id) + '.dump')
        if tb_file.exists():
            stb = joblib.load(tb_file)
            exc_type, exc_value, tb = from_serializable_traceback(stb)
            traceback = Traceback(exc_type, exc_value, tb)
            for frame in traceback.frames:
                flask_app.debugged_application.frames[frame.id] = frame
            flask_app.debugged_application.tracebacks[traceback.id] = traceback
            now = datetime.datetime.now()
            flask_app.tb_sessions[traceback.id] = (traceback, tb_id, now)
            return redirect(url_for('session_view', session_id=traceback.id))
        else:
            print(f"[err] No file {tb_file}")
            return jsonify({"success": False, "error": f"no TB with id {tb_id}"})

    @app.route('/tb/<tb_id>', methods=['POST'])
    def tb_upload(tb_id):
        try:
            tb_file = storage_dir / (str(tb_id) + '.dump')
            with open(tb_file, 'wb') as f:
                while not request.stream.is_exhausted:
                    f.write(request.stream.read(1024 * 100))
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
        else:
            return jsonify({'success': True, 'message': 'File uploaded'})

    @app.route('/last_session')
    def last_session():
        flask_app = app
        all_tb = list(flask_app.debugged_application.tracebacks.values())
        traceback = all_tb[-1]
        return render_traceback(traceback)

    @app.route('/session/<session_id>')
    def session_view(session_id):
        flask_app = app
        traceback = flask_app.tb_sessions[int(session_id)][0]
        return render_traceback(traceback)

    @app.route('/clear-sessions')
    def clear_sessions():
        flask_app = app
        tracebacks = flask_app.debugged_application.tracebacks
        frames = flask_app.debugged_application.frames

        for frame in frames.values():
            for var in frame.locals.values():
                if isinstance(var, pd.DataFrame):
                    df = var
                    df.drop(df.columns, axis=1, inplace=True)
                    df.drop(df.index, inplace=True)
            for var in frame.globals.values():
                if isinstance(var, pd.DataFrame):
                    df = var
                    df.drop(df.columns, axis=1, inplace=True)
                    df.drop(df.index, inplace=True)
            frame.console._ipy.locals.clear()
            frame.console._ipy.globals.clear()

        frames.clear()
        tracebacks.clear()
        flask_app.tb_sessions.clear()
        gc.collect()
        return 'cleared'

    @app.route('/')
    def home():
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
        sessions = get_current_sessions(app)
        process = psutil.Process(os.getpid())
        mem_used = pretty_size(process.memory_info().rss)
        return render_template(
            'index.html',
            files=files,
            sessions=sessions,
            mem_used=mem_used,
        )

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
