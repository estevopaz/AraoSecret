'''
Ichecker controllers.
'''

import datetime
import logging

import flask

import hoot

import controllers.common


LOGGER = logging.getLogger(__name__)


def _get_test(advertiser):
    '''
    Get data from test.
    '''
    test = None
    url = None
    for url in flask.request.form.getlist('test_url[]'):
        if url.strip().lower().startswith('http'):
            break
    if url:
        # Request
        test = hoot.tools.ichecker.extract(advertiser, url, sources=True)
    return test


def _get_output(advertiser_id):
    '''
    Get advertiser outputs.
    '''
    # Output data
    output = {'db': None}
    try:
        output['db'] = hoot.db.anadb.DB(advertiser_id).Table('AdWords').updated()
    except hoot.db.anadb.AnaDBError as error:
        LOGGER.warning(error)
    return output


def _get_urls(advertiser_id):
    '''
    Get list of Final URLs from AdWords.
    '''
    try:
        return (hoot.db.anadb.DB(advertiser_id).Table('AdWords')
                .select({'Final URL': 'distinct'})
                .where('date = "{}"'.format(datetime.date.today()))
                .read()['Final URL'].sort_values().tolist())
    except hoot.db.anadb.AnaDBError as error:
        LOGGER.warning(error)
        return list()


def panel(db_session, advertiser_id):
    '''
    Ichecker panel controller.
    '''
    advertiser = hoot.db.query.advertiser(db_session, advertiser_id)

    # Configuration
    if 'ichecker_update' in flask.request.form:

        if advertiser.ichecker_settings:
            # Update
            ichecker_settings = advertiser.ichecker_settings
        else:
            # New
            ichecker_settings = hoot.db.model.ICheckerSettings(advertiser.id_)
            db_session.add(ichecker_settings)

        # Method
        ichecker_settings.method = flask.request.form.get('method', 'GET')

        # No inventory text (no_inv_txt)
        ichecker_settings.no_inv_txt = flask.request.form.get('no_inv_txt')

        # No inventory URL (no_inv_url)
        ichecker_settings.no_inv_url = flask.request.form.get('no_inv_url')

        # Commit
        db_session.commit()

    return flask.render_template(
        'ichecker.html',
        advertiser=advertiser,
        advertisers=hoot.db.query.advertisers(db_session),
        adwords_stats=controllers.common.adwords_statistics(advertiser),
        icheck_stats=controllers.common.ichecker_statistics(advertiser_id),
        dataset=controllers.common.get_dataset(
            advertiser_id, 'AdWords',
            columns=['Campaign', 'AdGroup', 'AdGroup Status', 'AdGroup status change',
                     'Status conflicting', 'Final URL', 'Status', 'HTTP Code', 'Count',
                     'Price min.']),
        output=_get_output(advertiser_id),
        urls=_get_urls(advertiser.id_),
        test=_get_test(advertiser),
        yesterday=(datetime.date.today() - datetime.timedelta(days=1))
    )


def download(advertiser_id):
    '''
    Sitemap data down-loader controller.
    '''
    dataframe = (hoot.db.anadb.DB(advertiser_id).Table('AdWords')
                 .where('date = "{}"'.format(datetime.date.today())).read())
    file_name = 'URLs_{}'.format(advertiser_id)
    return hoot.web.common.send_dataframe(dataframe, file_name)
