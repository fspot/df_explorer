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
                'Interactive debugger <em>(you have access to your local variables)</em>'
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


def monkey_patch_frame(Frame):
    def my_init(self, exc_type, exc_value, tb):
        if not hasattr(tb, 'filename'):
            return self._original_init(exc_type, exc_value, tb)
        self.lineno = tb.tb_lineno
        self.function_name = tb.tb_frame.f_code.co_name
        self.locals = tb.tb_frame.f_locals
        self.globals = tb.tb_frame.f_globals
        self.filename = tb.filename
        self.sourcecode = tb.sourcecode
        self.module = self.globals.get('__name__')
        self.loader = self.globals.get('__loader__')
        self.code = tb.tb_frame.f_code
        self.hide = self.locals.get('__traceback_hide__', False)
        self.info = None

    def my_sourcelines(self):
        if not hasattr(self, 'sourcecode'):
            return self._original_sourcelines
        return self.sourcecode.splitlines()

    Frame._original_init = Frame.__init__
    Frame.__init__ = my_init
    Frame._original_sourcelines = Frame.sourcelines
    Frame.sourcelines = property(my_sourcelines)
