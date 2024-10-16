from flask.json.provider import DefaultJSONProvider
from datetime import datetime, date


class CustomJSONEncoder(DefaultJSONProvider):
    def default(self, obj):
        try:
            if isinstance(obj, date) or isinstance(obj, datetime):
                return obj.isoformat(sep=" ")
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return super().default(obj)
