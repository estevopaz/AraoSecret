'''
Sitemap controllers.
'''

import datetime
import logging
import os

import flask

import hoot

import controllers.common


LOGGER = logging.getLogger(__name__)


def _get_output(advertiser_id):
    '''
    Get advertiser outputs.
    '''
    output = {'db': None, 'ads_customizers': None}

    try:
        output['db'] = hoot.db.anadb.DB(advertiser_id).Table('AdWords').updated()
    except hoot.db.anadb.AnaDBError as error:
        LOGGER.warning(error)

    path = os.path.join(hoot.conf.reports_path(advertiser_id), 'ad_customizers_feed.csv')
    if os.path.exists(path):
        output['ads_customizers'] = datetime.datetime.fromtimestamp(int(os.path.getmtime(path)))

    return output


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
        test = hoot.tools.icounter.extract(advertiser, url)
    return test


def _get_urls(advertiser_id):
    '''
    Get list of Final URLs from AdWords.
    Filtered by iChecker (Status == "good url").
    '''
    try:
        return (hoot.db.anadb.DB(advertiser_id).Table('AdWords')
                .select({'Final URL': 'distinct'})
                .where(['date = "{}"'.format(datetime.date.today()),
                        'Status = "good url"'])
                .read()['Final URL'].sort_values().tolist())
    except hoot.db.anadb.AnaDBError as error:
        LOGGER.warning(error)
        return list()


def download(advertiser_id):
    '''
    Sitemap data down-loader controller.
    '''
    dataframe = (hoot.db.anadb.DB(advertiser_id).Table('AdWords')
                 .where('date = "{}"'.format(datetime.date.today())).read())
    file_name = 'Inventory Counter {}'.format(advertiser_id)
    return hoot.web.common.send_dataframe(dataframe, file_name)


def panel(db_session, advertiser_id):
    '''
    Sitemap configuration panel controller.
    '''
    advertiser = hoot.db.query.advertiser(db_session, advertiser_id)

    # Configuration
    if 'icounter_update' in flask.request.form:

        if advertiser.icounter_settings:
            # Update
            icounter_settings = advertiser.icounter_settings
        else:
            # New
            icounter_settings = hoot.db.model.ICounterSettings(advertiser.id_)
            db_session.add(icounter_settings)

        # Version
        icounter_settings.version = '2.0'

        # Method
        icounter_settings.method = flask.request.form.get('method', 'GET')

        # URL Sort Addon (url_sort_addon)
        icounter_settings.url_sort_addon = flask.request.form.get('url_sort_addon', None)

        # URL Remove Addon (url_remove_addon)
        icounter_settings.url_remove_addon = flask.request.form.get('url_remove_addon', None)

        # Count Pattern (count_pattern)
        patterns = flask.request.form.getlist('count_pattern[]')
        patterns = [pattern for pattern in patterns if pattern.strip() != '']
        if patterns:
            icounter_settings.count_pattern = ' | '.join(patterns)
        else:
            icounter_settings.count_pattern = None

        # Price Pattern (price_pattern)
        patterns = flask.request.form.getlist('price_pattern[]')
        patterns = [pattern for pattern in patterns if pattern.strip() != '']
        if patterns:
            icounter_settings.price_pattern = ' | '.join(patterns)
        else:
            icounter_settings.price_pattern = None

        # Commit
        db_session.commit()

    return flask.render_template(
        'icounter.html',
        advertiser=advertiser,
        advertisers=hoot.db.query.advertisers(db_session),
        adwords_stats=controllers.common.adwords_statistics(advertiser),
        icount_stats=controllers.common.icounter_statistics(advertiser_id),
        dataset=controllers.common.get_dataset(
            advertiser_id, 'AdWords',
            columns=['Campaign', 'AdGroup', 'AdGroup Status', 'AdGroup status change',
                     'Status conflicting', 'Final URL', 'Status', 'HTTP Code', 'Count',
                     'Price min.']),
        output=_get_output(advertiser_id),
        urls=_get_urls(advertiser_id),
        test=_get_test(advertiser)
    )
