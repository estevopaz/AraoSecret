'''
Campaign generation controller.
'''

import hoot


def download(db_session, template_id):
    '''
    Generate campaign and send as CSV.
    '''
    generator = hoot.adwords.campaign.Generator(db_session, template_id)
    return hoot.web.common.send_dataframe(generator.all(),
                                          generator.campaign_template.accountname.replace(' ', '_'),
                                          'utf-8-sig')
