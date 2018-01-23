'''
Sitemap controllers.
'''

import datetime
import logging
import os

import flask
import requests
import sqlalchemy

import hoot

import controllers.common


LOGGER = logging.getLogger(__name__)


def _get_output(advertiser_id):
    '''
    Get advertiser outputs.
    '''
    output = {
        'db': None,
        'adwords_dynamic_remarketing_feed': None,
        'adwords_dynamic_remarketing_feed_new': None,
        'adwords_dynamic_remarketing_feed_used': None,
        'facebook_dynamic_remarketing_feed': None,
    }

    try:
        output['db'] = hoot.db.anadb.DB(advertiser_id).Table('Sitemap').updated()
    except hoot.db.anadb.AnaDBError as error:
        LOGGER.warning(error)

    for key in output.keys() - {'db'}:
        path = os.path.join(hoot.conf.reports_path(advertiser_id), key + '.csv')
        if os.path.exists(path):
            output[key] = datetime.datetime.fromtimestamp(int(os.path.getmtime(path)))

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
        # Request
        test = hoot.tools.sitemap.extract(advertiser, url,
                                          attach_sources=True, attach_derivative=True)
    return test


def _get_urls(advertiser):
    '''
    Get URLs from sitemap URL.
    '''
    urls = None
    if advertiser.sitemap_settings and advertiser.sitemap_settings.sitemap_url:
        try:
            urls = hoot.data_extractor.get_urls(
                advertiser.sitemap_settings.sitemap_url,
                matches=advertiser.sitemap_settings.filter_urls_by_match,
                vin_filter=advertiser.sitemap_settings.filter_urls_with_vin,
                headers=advertiser.get_http_headers())
        except requests.exceptions.MissingSchema:
            pass
    return urls


def _save_custom_values(db_session, advertiser):
    '''
    Save custom title and/or description.

    Note: Color is the default because first, so can be twice on array.
    '''
    # Update or remove
    for i in range(10):
        attribute_id = flask.request.form.get('attribute_id_{}'.format(i))
        if attribute_id:
            attribute = (db_session.query(hoot.db.model.SitemapXPaths)
                         .filter(hoot.db.model.SitemapXPaths.id_ == attribute_id)
                         .one())
            attribute_pattern = flask.request.form.get('attribute_pattern_{}'.format(i)).strip()
            # Update
            if attribute_pattern:
                attribute.xpath = attribute_pattern
                attribute.remove_chars = flask.request.form.get('attribute_remove_chars_{}'
                                                                .format(i)).strip()
                attribute.remove_phrase = flask.request.form.get('attribute_remove_phrase_{}'
                                                                 .format(i)).strip()
                attribute.failsafe = 'attribute_failsafe_{}'.format(i) in flask.request.form
            # Remove
            else:
                db_session.delete(attribute)
    # Add
    for i in range(10):
        attribute_type = flask.request.form.get('attribute_type_{}'.format(i))
        if attribute_type == 'common':
            attribute_name = flask.request.form.get('new_attribute_common_name_{}'
                                                    .format(i)).strip()
        else:
            attribute_name = flask.request.form.get('new_attribute_free_name_{}'.format(i)).strip()
        attribute_pattern = flask.request.form.get('new_attribute_pattern_{}'.format(i)).strip()
        if attribute_name and attribute_pattern:
            db_session.add(hoot.db.model.SitemapXPaths(
                advertiser.id_, attribute_name, attribute_pattern,
                flask.request.form.get('new_attribute_remove_chars_{}'.format(i)).strip(),
                flask.request.form.get('new_attribute_remove_phrase_{}'.format(i)).strip(),
                'new_attribute_failsafe_{}'.format(i) in flask.request.form
            ))


def download(advertiser_id):
    '''
    Sitemap data down-loader controller.
    '''
    dataframe = hoot.db.fast.sitemap_all(advertiser_id)
    file_name = 'URLs_{}'.format(advertiser_id)
    return hoot.web.common.send_dataframe(dataframe, file_name)


def panel(db_session, advertiser_id):
    '''
    Sitemap configuration panel controller.
    '''
    advertiser = hoot.db.query.advertiser(db_session, advertiser_id)

    # Configuration
    if flask.request.form.get('action') == 'update':

        # Tracking data
        if advertiser.request_script:
            # Update
            request_script = advertiser.request_script
        else:
            request_script = hoot.db.model.RequestScript(advertiser.id_)
            db_session.add(request_script)
        request_script.adwords_conversion_id = flask.request.form.get('adwords_conversion_id')
        request_script.facebook_pixel_id = flask.request.form.get('facebook_pixel_id')
        request_script.gtm_privileges = flask.request.form.get('gtm_privileges', False)

        # Sitemap settings
        if advertiser.sitemap_settings:
            # Update
            sitemap_settings = advertiser.sitemap_settings
        else:
            # New
            sitemap_settings = hoot.db.model.SitemapSettings(advertiser.id_)
            db_session.add(sitemap_settings)
        # Version
        sitemap_settings.version = '2.0'
        # Sitemap
        input_multi = flask.request.form.getlist('sitemap_url[]')
        input_multi = [value for value in input_multi if value.strip() != '']
        sitemap_settings.sitemap_url = '[OR]'.join(input_multi)
        # Filter VIN
        sitemap_settings.filter_urls_with_vin = (
            flask.request.form.get('filter_urls_with_vin', False)
        )
        # Filter text on URLs
        input_multi = flask.request.form.getlist('filter_urls_by_match[]')
        input_multi = [value for value in input_multi if value.strip() != '']
        if input_multi:
            sitemap_settings.filter_urls_by_match = '[OR]'.join(input_multi)
        else:
            sitemap_settings.filter_urls_by_match = None
        # Price
        input_multi = flask.request.form.getlist('price_match_pattern[]')
        input_multi = [value for value in input_multi if value.strip() != '']
        if input_multi:
            sitemap_settings.price_match_pattern = '[OR]'.join(input_multi)
        else:
            sitemap_settings.price_match_pattern = None
        # Image
        input_multi = flask.request.form.getlist('image_base_url[]')
        input_multi = [value for value in input_multi if value.strip() != '']
        if input_multi:
            sitemap_settings.image_base_url = '[OR]'.join(input_multi)
        else:
            sitemap_settings.image_base_url = None
        # Image exclusion
        input_multi = flask.request.form.getlist('image_to_exclude[]')
        input_multi = [value for value in input_multi if value.strip() != '']
        if input_multi:
            sitemap_settings.image_to_exclude = '[OR]'.join(input_multi)
        else:
            sitemap_settings.image_to_exclude = None
        sitemap_settings.image_min_size_x = flask.request.form.get('image_min_size_x')
        sitemap_settings.image_min_size_y = flask.request.form.get('image_min_size_y')
        sitemap_settings.image_save_2nd = flask.request.form.get('image_save_2nd', False)

        # Request method
        sitemap_settings.method = flask.request.form.get('method')

        # Custom title and/or description
        _save_custom_values(db_session, advertiser)

        # Reports data
        sitemap_settings.days_ago = flask.request.form.get('days_ago')
        sitemap_settings.min_decrease = flask.request.form.get('min_decrease')
        sitemap_settings.old = flask.request.form.get('old', False)

        # Commit
        db_session.commit()

    return flask.render_template(
        'sitemap.html',
        advertiser=advertiser,
        advertisers=hoot.db.query.advertisers(db_session),
        adwords_stats=controllers.common.adwords_statistics(advertiser),
        sitemap_stats=controllers.common.sitemap_statistics(advertiser_id),
        dataset=controllers.common.get_dataset(
            advertiser_id, 'Sitemap',
            columns=['Title', 'Condition', 'Price', 'Description', 'VIN', 'URL', 'Image URL']),
        output=_get_output(advertiser_id),
        urls=_get_urls(advertiser),
        test=_get_test(advertiser)
    )
