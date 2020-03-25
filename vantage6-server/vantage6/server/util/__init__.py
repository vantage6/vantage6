import vantage6.common.colorer


def logger_name(special__name__):
    log_name = special__name__.split('.')[-1]
    if len(log_name) > 14:
        log_name = log_name[:11] + ".."
    return log_name

class Singleton(type):
    _instances = {} 

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super(Singleton, cls).__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]

def prepare_bytes_for_transport(bytes_):
    return base64.b64encode(bytes_).decode(constants.STRING_ENCODING)

def unpack_bytes_from_transport(bytes_string):
    return base64.b64decode(bytes_string.encode(constants.STRING_ENCODING))

