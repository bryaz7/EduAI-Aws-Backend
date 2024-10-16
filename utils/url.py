from urllib.parse import urlparse


def is_url(string):
    try:
        result = urlparse(string)
        return all([result.scheme, result.netloc])
    except Exception:
        return False
