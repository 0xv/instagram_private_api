import json
import codecs
import datetime
import os.path
import logging
import argparse
try:
    import instagram_private_api as app_api
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    import instagram_private_api as app_api


def to_json(python_object):
    if isinstance(python_object, bytes):
        return {'__class__': 'bytes',
                '__value__': codecs.encode(python_object, 'base64').decode()}
    raise TypeError(repr(python_object) + ' is not JSON serializable')


def from_json(json_object):
    if '__class__' in json_object:
        if json_object['__class__'] == 'bytes':
            return codecs.decode(json_object['__value__'].encode(), 'base64')
    return json_object


def onlogin_callback(api, new_settings_file):
    cache_settings = api.settings
    with open(new_settings_file, 'w') as outfile:
        json.dump(cache_settings, outfile, default=to_json)
        print('SAVED: %s' % new_settings_file)


if __name__ == '__main__':

    logging.basicConfig()
    logger = logging.getLogger('instagram_private_api')
    logger.setLevel(logging.WARNING)

    # Example command:
    # python examples/savesettings_logincallback.py -u "yyy" -p "zzz" -settings "test_credentials.json"
    parser = argparse.ArgumentParser(description='login callback and save settings demo')
    parser.add_argument('-settings', '--settings', dest='settings_file_path', type=str, required=True)
    parser.add_argument('-u', '--username', dest='username', type=str, required=True)
    parser.add_argument('-p', '--password', dest='password', type=str, required=True)
    parser.add_argument('-debug', '--debug', action='store_true')

    args = parser.parse_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)

    print('Client version: %s' % app_api.__version__)

    try:

        settings_file = args.settings_file_path
        if not os.path.isfile(settings_file):
            # settings file does not exist
            print('Unable to find file: %s' % settings_file)

            # login new
            api = app_api.Client(
                args.username, args.password,
                on_login=lambda x: onlogin_callback(x, args.settings_file_path))
        else:
            with open(settings_file) as file_data:
                cached_settings = json.load(file_data, object_hook=from_json)
            print('Reusing settings: %s' % settings_file)

            # reuse auth settings
            api = app_api.Client(
                args.username, args.password,
                settings=cached_settings)

    except (app_api.ClientCookieExpiredError, app_api.ClientLoginRequiredError) as e:
        print('ClientCookieExpiredError/ClientLoginRequiredError: %s' % e)

        # Login expired
        # Do relogin but use default ua, keys and such
        api = app_api.Client(
            args.username, args.password,
            on_login=lambda x: onlogin_callback(x, args.settings_file_path))

    except app_api.ClientLoginError as e:
        print('ClientLoginError %s' % e)
        exit(9)
    except app_api.ClientError as e:
        print('ClientError %s (Code: %d, Response: %s)' % (e.msg, e.code, e.error_response))
        exit(9)
    except Exception as e:
        print('Unexpected Exception: %s' % e)
        exit(99)

    # Show when login expires
    cookie_expiry = api.cookie_jar.expires_earliest
    print('Cookie Expiry: %s' % datetime.datetime.fromtimestamp(cookie_expiry).strftime('%Y-%m-%dT%H:%M:%SZ'))

    # Call the api
    results = api.tag_search('cats')
    assert len(results.get('results', [])) > 0

    print('All ok')
