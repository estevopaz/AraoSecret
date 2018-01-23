'''
Hoot configuration manager.
'''

import configparser as _configparser
import logging as _logging
import logging.config as _logging_config
import os
import yaml as _yaml


_LOGGER = _logging.getLogger(__name__)


PATH_MODULE = os.path.abspath(os.path.dirname(__file__))
PATH_PROJECT = PATH_MODULE[:-len('arao_secret')]


CONF_PATH = '/etc/arao_secret/main.conf'
CONF = _configparser.ConfigParser(allow_no_value=True)
CONF.read(os.path.expanduser(CONF_PATH))


def get(section, key, data_type=str):
    '''
    Get configured parameter.
    '''
    try:
        if data_type == bool:
            return CONF.getboolean(section, key)
        elif data_type == int:
            return CONF.getint(section, key)
        elif data_type == float:
            return CONF.getfloat(section, key)
        else:
            return CONF.get(section, key)
    except _configparser.NoSectionError as nse:
        _LOGGER.error(nse)
        raise Exception('Please check inside "{}" file, "{}" section and "{}" attribute !'
                        .format(CONF_PATH, section, key))


def get_log_file(command, advertiser_id):
    '''
    Get log file according to given advertiser.
    '''
    # Check advertiser
    if isinstance(advertiser_id, list) and len(advertiser_id) == 1:
        advertiser_id = str(advertiser_id[0])
    elif isinstance(advertiser_id, (int, str)):
        advertiser_id = str(advertiser_id)
    else:
        advertiser_id = None

    # Set log file according to command
    log_file = command.split()[0]
    log_file = log_file.replace('Hoot-', '')
    log_file = log_file + '.log'
    if advertiser_id:
        log_file = os.path.join(get('Main', 'log_path'), advertiser_id, log_file)
    else:
        log_file = os.path.join(get('Main', 'log_path'), log_file)

    # Ensure path
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    return log_file


def get_logger(name, advertiser_id, level=None):
    '''
    Configure the logging and create a logger for the current module.
    '''
    # Get logging configuration
    _file = open(os.path.join(PATH_PROJECT, 'conf', 'logging.yml'))
    log_dict = _yaml.load(_file)
    _file.close()

    # Replace console level
    if level:
        log_dict['handlers']['console']['level'] = level

    # Create a different log for each advertiser if proceed
    log_dict['handlers']['file']['filename'] = get_log_file(name, advertiser_id)

    # Filling e-Mail configuration
    log_dict['handlers']['email']['mailhost'] = [get('Email', 'server'), get('Email', 'smtp_port')]
    log_dict['handlers']['email']['fromaddr'] = get('Email', 'from')
    log_dict['handlers']['email']['toaddrs'] = get('Main', 'errors_to')
    log_dict['handlers']['email']['credentials'] = [get('Email', 'user'), get('Email', 'pass')]

    _logging_config.dictConfig(log_dict)
    return _logging.getLogger(name)


def reports_path(advertiser_id):
    '''
    Get output path for reports.
    '''
    path = str(get('Outputs', 'reports_path'))
    path = path.replace('$ADVERTISER_ID', str(advertiser_id))
    return path
