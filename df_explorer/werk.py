import mimetypes
from os.path import join, dirname, basename

from werkzeug import run_simple
from werkzeug.wrappers import BaseResponse as Response


def monkey_patch_debugged_application(DebuggedApplication):
    def my_init(self, app, *args, **kwargs):
        app.debugged_application = self
        self._original_init(app, *args, **kwargs)

    def my_get_resource(self, request, filename):
        if filename in ['debugger.js', 'style.css']:
            filename = join(dirname(__file__), 'shared', basename(filename))
            mimetype = mimetypes.guess_type(filename)[0] \
                or 'application/octet-stream'
            f = open(filename, 'rb')
            try:
                return Response(f.read(), mimetype=mimetype)
            finally:
                f.close()
        else:
            return self._original_get_resource(request, filename)

    DebuggedApplication._original_init = DebuggedApplication.__init__
    DebuggedApplication._original_get_resource = DebuggedApplication.get_resource
    DebuggedApplication.__init__ = my_init
    DebuggedApplication.get_resource = my_get_resource


def monkey_patch_flask_run(Flask):
    def my_run(self, host, port, debug=None, **options):
        if debug is not None:
            self.debug = bool(debug)
        options.setdefault('use_reloader', self.debug)
        options.setdefault('use_debugger', self.debug)
        try:
            run_simple(host, port, self, **options)
        finally:
            self._got_first_request = False

    Flask.run = my_run


def monkey_patch_traceback(Traceback):
    def my_init(self, *args, **kwargs):
        self._original_init(*args, **kwargs)
        if self.frames:
            last_frame = self.frames[-1]
            self.frames.clear()
            self.frames.append(last_frame)

    def my_render_full(self, *args, **kwargs):
        ret = self._original_render_full(*args, **kwargs)
        REPLACE = [
            (
                "Traceback <em>(most recent call last)</em>",
                'Interactive debugger <em>(you can access your dataframe through the "df" variable)</em>'
            ),
            (
                "The debugger caught an exception in your WSGI application.",
                ""
            ),
            ("You can now", ""),
            ("look at the traceback which led to the error.", ""),
        ]
        for old, new in REPLACE:
            ret = ret.replace(old, new)
        return ret

    Traceback._original_init = Traceback.__init__
    Traceback._original_render_full = Traceback.render_full
    Traceback.__init__ = my_init
    Traceback.render_full = my_render_full
