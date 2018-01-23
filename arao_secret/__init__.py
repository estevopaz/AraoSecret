'''
Imports done in init to navigate easily through the lib.
'''

from arao_secret import conf
from arao_secret import db
from arao_secret import helper
from arao_secret import manager


ENCODING = 'UTF-8'

# Follow key is used to offuscate users master password in memory
# During user session, we need its master password to decrypt his linked secrets
# Keep in mind that this is just offuscation, if a system user can dump memory,
# he won't see the clear password, but still can decrypt it identifing where this credentials are
# Note: We can't use multiple workers in uwsgi, because we would create multiple keys ???
APP_KEY = {
    'aes_iv': helper.aes_iv_gen(),
    'aes_key': helper.aes_key_gen(),
}
