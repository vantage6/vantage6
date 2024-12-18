import logging
import logging.config

log_level="DEBUG"
k8s_log_level="INFO"

def logs_setup()->None:
    logging_config = {
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'simple': {
                'format': '%(asctime)s [%(levelname)s] %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            },
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'simple',
            },
        },
        'loggers': {
            'kubernetes': {
                'handlers': ['console'],
                'level': k8s_log_level,
                'propagate': False,
            },
        },
    }

    logging.config.dictConfig(logging_config)