'''
Hoot commands manager.
'''

import flask

import hoot


def run(command, advertiser_id, data=None):
    '''
    Launch Hoot job.
    '''
    try:
        if data:
            hoot.tools.jobs.run("{} --json '{}'".format(command, data))
        else:
            hoot.tools.jobs.run('{} {}'.format(command, advertiser_id))
    except RuntimeError:
        pass
    return flask.redirect(
        flask.url_for('view_status', command=command, advertiser_id=advertiser_id, data=data))


def status(command, advertiser_id, data=None):
    '''
    Status of Hoot job.
    '''
    if data:
        command = "{} --json '{}'".format(command, data)
    else:
        command = '{} {}'.format(command, advertiser_id)
    info = hoot.tools.jobs.get_info(command)
    log = hoot.tools.jobs.get_log(command, advertiser_id)
    return flask.render_template('job_status.html', command=command, info=info, log=log)
