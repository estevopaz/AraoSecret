'''
Advertiser controller.
'''

import flask
import flask_login

import hoot

from controllers import common


def main(db_session, advertiser_id):
    '''
    Advertiser main panel.
    '''
    if flask.request.method == 'POST':
        advertiser_id = flask.request.form['advertiser_id']
    if not advertiser_id:
        # Redirect to index when login with ?next=/advertiser and missing POST data
        return flask.redirect(flask.url_for('view_index'))

    advertiser = hoot.db.query.advertiser(db_session, advertiser_id)
    if flask.request.method == 'POST' and 'advertiser_update' in flask.request.form:
        # Admin permissions
        if flask_login.current_user.has_role('admin'):
            advertiser.accountname = flask.request.form.get('name')
            advertiser.website = flask.request.form.get('website')
            if flask.request.form.get('cms'):
                advertiser.cmsid = flask.request.form.get('cms')
            else:
                advertiser.cmsid = None
            advertiser.active = flask.request.form.get('active', False)
            advertiser.address = flask.request.form.get('address')
            advertiser.city = flask.request.form.get('city')
            advertiser.state = flask.request.form.get('state')
            advertiser.zip_code = flask.request.form.get('zip_code')
            advertiser.country = flask.request.form.get('country')
            advertiser.latitude = flask.request.form.get('latitude')
            advertiser.longitude = flask.request.form.get('longitude')
            advertiser.googleid = flask.request.form.get('adwords_account')
            advertiser.google_label_filter = flask.request.form.get('google_label_filter')
        # Sitemap permissions
        if flask_login.current_user.has_role('sitemap'):
            advertiser.scrawler_active = flask.request.form.get('scrawler_active', False)
        # iChecker permission
        if flask_login.current_user.has_role('ichecker'):
            advertiser.ichecker_active = flask.request.form.get('ichecker_active', False)
            if flask_login.current_user.has_role('sitemap'):
                advertiser.ichecker_from_sitemap = flask.request.form.get('ichecker_from_sitemap',
                                                                          False)
        # iCounter permissions
        if flask_login.current_user.has_role('icounter'):
            advertiser.icounter_active = flask.request.form.get('icounter_active', False)
        db_session.commit()

    return flask.render_template(
        'advertiser.html',
        advertiser=advertiser,
        advertisers=hoot.db.query.advertisers(db_session),
        cmss=db_session.query(hoot.db.model.CMS).all(),
        campaigns=hoot.report.campaign.status(advertiser),
        adwords_stats=common.adwords_statistics(advertiser),
        icheck_stats=common.ichecker_statistics(advertiser_id),
        icount_stats=common.icounter_statistics(advertiser_id),
        sitemap_stats=common.sitemap_statistics(advertiser_id)
    )


def get_datatable(advertisers):
    '''
    Create dataset data for DataTables.
    '''
    advertiser_table = {
        'columns': ['ID', 'Name', 'Active', 'Client', 'CMS', 'iChecker', 'iCounter', 'sCrawler',
                    'AdWords', 'Ad Groups', 'Enabled', 'Paused', 'Changed',
                    'URLs', 'Good', 'No inventory', 'Errors'],
        'data': list(),
        'order': [[2, 'asc'], [1, 'asc']]
    }
    for advertiser in advertisers:
        row = list()
        # ID link
        row.append('<a href="{}">{}</a>'
                   .format(flask.url_for('view_advertiser', advertiser_id=advertiser.id_),
                           advertiser.id_))
        # Name link
        row.append('<a href="{}">{}</a>'
                   .format(flask.url_for('view_advertiser', advertiser_id=advertiser.id_),
                           advertiser.accountname))
        row.append(advertiser.active)
        # Client link
        row.append('<a href="{}">{}</a>'
                   .format(flask.url_for('view_client', client_id=advertiser.clientid),
                           advertiser.client))
        row.append(advertiser.cms)
        row.append(advertiser.ichecker_active)
        row.append(advertiser.icounter_active)
        row.append(advertiser.scrawler_active)
        row.append(advertiser.googleid)
        # Statistics
        if advertiser.statistics:
            row.append(advertiser.statistics.adgroups)
            row.append(advertiser.statistics.adgroups_enabled)
            row.append(advertiser.statistics.adgroups_paused)
            row.append(advertiser.statistics.changed_adgroup_statuses)
            row.append(advertiser.statistics.good_urls + advertiser.statistics.no_inventory_urls)
            row.append(advertiser.statistics.good_urls)
            row.append(advertiser.statistics.no_inventory_urls)
            row.append(advertiser.statistics.erroneous_urls)
        else:
            for _ in range(8):
                row.append(None)
        advertiser_table['data'].append(hoot.web.common.list_to_javascript(row))
    return advertiser_table


def show_list(db_session):
    '''
    Advertisers list controller.
    '''
    return flask.render_template(
        'advertiser_list.html',
        advertisers=hoot.db.query.advertisers(db_session),
        advertisers_table=get_datatable(db_session.query(hoot.db.model.Advertiser).all())
    )
