import logging
import functools


def deprecated(alternative_funcs=None):
    """Deprecation indicator of a function. Whenever a function is wrapped with this decorator, it will show
        a warning message."""
    if alternative_funcs is None:
        alternative_funcs = []

    def decorator(func):
        @functools.wraps(func)
        def new_func(*args, **kwargs):
            warning_message = f"Function {func.__name__} is deprecated. "
            if alternative_funcs:
                warning_message += f"Use {', '.join(alternative_funcs)} instead."
            logging.warning(warning_message)
            return func(*args, **kwargs)
        return new_func
    return decorator
