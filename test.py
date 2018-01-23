
import arao_secret

db_session = arao_secret.db.create_session()
arao_secret.db.create_tables(db_session)

user = arao_secret.manager.get_user(db_session, 'alias_test', 'pass_test')
user.list_groups()
print('')
group_id = int(input('Select Group ID: '))
print('')
user.list_secrets(db_session, group_id)
print('')
secret_id = int(input('Select Secret ID: '))
print('')
user.show_secret(db_session, secret_id)
exit(0)

user = arao_secret.manager.create_user(db_session, 'alias_test', 'email_test', 'pass_test')
group, user_group_key = user.create_group(db_session, 'group_test')
secret = user.create_secret(db_session, user_group_key, 'name_test', 'url_test', 'login_test',
                                                        'password_test', 'comment_test')


# TODO : Delete secret
# TODO : Delete group
# TODO : Delete user
# TODO : Configure logger
# TODO : Manage duplicated errors
# TODO : List user groups
# TODO : List group secrets
# TODO : Share group with another user
# TODO : Send email for registration from one user
