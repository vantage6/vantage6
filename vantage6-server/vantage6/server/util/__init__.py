from vantage6.common import Singleton, logger_name, bytes_to_base64s, base64s_to_bytes


def log_full_request(request, log=None):
    if log is None:
        stack = inspect.stack()
        calling = stack[1]
        filename = os.path.split(calling.filename)[-1]
        module_name = os.path.splitext(filename)[0]

        log = logging.getLogger(module_name)

    log.info(f'{request.method}: {request.url}')
    log.info(f'  request.args: {request.args}')
    log.info(f'  request.data: {request.get_data()}')

    if request.is_json and len(request.data):
        log.info(f'  request.json: {request.json}')

    log.info(f'  headers:')
    for header in str(request.headers).splitlines():
        log.info(f'    ' + header)
