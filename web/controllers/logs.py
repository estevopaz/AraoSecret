'''
Logs controller.
'''

import datetime

import flask
import glob
import os
import re
import jinja2

import hoot

def main(advertiser_id):
    '''
    Print application logs.
    '''
    log_path = hoot.conf.get('Main', 'log_path')
    file_list = ['cron_sitemap_crawler_all.log', 'cron_advertiser_all.log']

    if advertiser_id:
        log_path = os.path.join(log_path, str(advertiser_id))
        file_list = [os.path.basename(x) for x in glob.glob(os.path.join(log_path, '*.log*'))]

    log = ['Log file still no selected.']
    if flask.request.method == 'POST' and 'file' in flask.request.form:
        if flask.request.form.get('file', None) in file_list:
            log_file = open(os.path.join(log_path, flask.request.form.get('file')))
            log = log_file.readlines()
            log_file.close()
        else:
            log = ['ERROR : File not found in logs path !']

    log_formated = list()
    for line in log:
        return_pos = line.rfind('\r')
        if return_pos != -1:
            line = line[return_pos + 1:]
        line = line.strip()
        if line:
            log_formated.append(line)

    return flask.render_template('logs.html', file_list=file_list, log=log_formated)
