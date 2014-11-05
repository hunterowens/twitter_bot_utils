import tweepy
import itertools
from os import path, getcwd
from . import helpers

CONFIG_DIRS = [
    '~',
    '~/bots',
]

CONFIG_BASES = [
    'botrc',
    'bots.yaml',
    'bots.json'
]


def _find_config_file(config_file=None, config_list=None):
    '''Search for a file in a list of files'''

    config_list = config_list or []
    dirs = [getcwd()] + CONFIG_DIRS

    for _dir, _base in itertools.product(dirs, CONFIG_BASES):
        config_list.append(path.join(_dir, _base))

    if config_file:
        config_list = [config_file] + config_list

    for pth in config_list:

        expanded = path.expanduser(pth)
        if path.exists(expanded):
            return expanded


def _setup_auth(user_conf, app_conf, **kwargs):
    '''Setup tweepy authentication using passed args or config file settings'''

    consumer_key = kwargs.get('consumer_key') or app_conf['consumer_key']
    consumer_secret = kwargs.get('consumer_secret') or app_conf['consumer_secret']

    key = kwargs.get('key') or user_conf['key']
    secret = kwargs.get('secret') or user_conf['secret']

    auth = tweepy.OAuthHandler(consumer_key=consumer_key, consumer_secret=consumer_secret)
    auth.set_access_token(key=key, secret=secret)

    return auth


class API(tweepy.API):

    '''Extends the tweepy API with config-file handling'''

    _app_name, _screen_name = None, None

    _config, _user_conf, _app_conf = {}, {}, {}

    _protected_info = ['apps', 'users', 'consumer_key', 'consumer_secret', 'key', 'secret', 'app']

    _last_tweet, _last_reply, _last_retweet = None, None, None

    def __init__(self, screen_name, parsed_args=None, **kwargs):
        # Optionally used args from argparse.ArgumentParser
        if parsed_args:
            try:
                args = dict((k, v) for k, v in vars(parsed_args).items() if v is not None)
                kwargs.update(**args)
            except TypeError:
                # probably didn't get a Namespace() for passed args
                pass

        self._screen_name = screen_name

        # get config file and parse it
        try:
            # Use passed config file, or look for it in the paths above
            file_name = _find_config_file(kwargs.get('config'))
            file_config = helpers.config_parse(file_name)

        except (AttributeError, IOError):
            if kwargs.get('config'):
                msg = 'Custom config file not found: {0}'.format(kwargs['config'])

            else:
                msg = 'Config file not found in ~/bots.{json,yaml}, ~/bots/bots.{json,yaml}, ~/botrc or ~/bots/botrc'

            raise IOError(msg)

        # kwargs take precendence over config file
        file_config.update(**kwargs)

        # set overall, app and user conf dicts
        self._config_setup(file_config)

        # setup auth
        try:
            auth = _setup_auth(self._user_conf, self._app_conf, **kwargs)

        except KeyError:
            raise KeyError("Incomplete config")

        # initiate api connection
        super(API, self).__init__(auth)

    def _conf_update(self, update=None):
        update = update or {}

        for k, v in update.items():
            if k not in self._protected_info:
                self._config[k] = v

    def _config_setup(self, file_config):
        '''Return object that holds config settings'''

        # Pull user and app data from the file
        self._app_name = file_config.get('users', {}).get(self.screen_name, {}).get('app')

        self._app_conf = file_config.get('apps', {}).get(self.app, {})
        self._user_conf = file_config.get('users', {}).get(self.screen_name, {})

        # Pull non-authentication settings from the file.
        # User, app, and general settings are included, in that order of preference
        self._conf_update(file_config)
        self._conf_update(self._app_conf)
        self._conf_update(self._user_conf)

    @property
    def config(self):
        return self._config

    @property
    def screen_name(self):
        return self._screen_name

    @property
    def app(self):
        return self._app_name

    @property
    def last_tweet(self):
        if not self._last_tweet:
            self._last_tweet = self.user_timeline().pop(0).id

        return self._last_tweet

    @property
    def last_reply(self):
        if not self._last_reply:
            tl = self.user_timeline()
            filtered = [tweet for tweet in tl if tweet.in_reply_to_user_id]
            self._last_reply = filtered[0].id

        return self._last_reply

    @property
    def last_retweet(self):
        if not self._last_retweet:
            tl = self.user_timeline()
            filtered = [tweet for tweet in tl if tweet.retweeted]
            self._last_retweet = filtered[0].id

        return self._last_retweet

