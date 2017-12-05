import io
import types

import joblib


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


# ~~~ Serialization related utils ~~~


def from_pickled_dict(d):
    def from_picklable(obj):
        if obj is None:
            return None
        try:
            f = io.BytesIO(obj)
            return joblib.load(f)
        except Exception:
            return None

    unpickled = {k: from_picklable(v) for k, v in d.items()}
    unpickling_failed = {k: v for k, v in unpickled.items() if v is None}
    unpickled = {k: v for k, v in unpickled.items() if v is not None}
    unpickled['__unpickling_failed__'] = list(unpickling_failed.keys())
    return unpickled


def from_serializable_traceback(d):
    tb = d['tb']
    tb = types.SimpleNamespace(**tb)
    tb.tb_frame = types.SimpleNamespace(**tb.tb_frame)
    tb.tb_frame.f_code = types.SimpleNamespace(**tb.tb_frame.f_code)
    tb.tb_frame.f_locals = from_pickled_dict(tb.tb_frame.f_locals)
    tb.tb_frame.f_globals = from_pickled_dict(tb.tb_frame.f_globals)
    return d['exc_type'], d['exc_value'], tb
