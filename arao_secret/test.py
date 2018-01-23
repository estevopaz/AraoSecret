
import arao_secret

user = arao_secret.db.model.User('alias', 'email', 'pass')
group = arao_secret.db.model.Group('group')

group_key = arao_secret.helper.aes_key_gen()
user_group_key = arao_secret.db.model.UserGroupKey(user, group, group_key)

secret = user_group_key.encrypt('pass', 'secret')
user_group_key.decrypt('pass', secret)
