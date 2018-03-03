"""
Django settings for the Rise project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'trd@o90gt%nigt*8=r-(jpcu$^no09ed9*)yo#$qflkodd9ypt'

SITE_ID = 1

# SECURITY WARNING: don't run with debug turned on in production!
STAGING = 'STAGING' in os.environ
PRODUCTION = 'PRODUCTION' in os.environ
DEV = 'DEV' in os.environ
DEBUG = not STAGING and not PRODUCTION and not DEV

TEMPLATE_DEBUG = True
TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'templates'),
)

if STAGING:
    ALLOWED_HOSTS = ['staging.iflyrise.com', 'stage.iflyrise.com']

if PRODUCTION:
    ALLOWED_HOSTS = ['production.iflyrise.com', 'members.iflyrise.com']

if DEV:
    ALLOWED_HOSTS = ['dev.iflyrise.com']

AUTH_USER_MODEL = 'accounts.User'
AUTH_PROFILE_MODULE = 'accounts.UserProfile'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/logged-in/'
LOGOUT_URL = '/logout/'

import braintree

if DEBUG or STAGING or DEV:
    # STRIPE_API_KEY = 'sk_test_4RztSfPlyj8EZ4LoBMAFGa8U' #old
    STRIPE_API_KEY = 'sk_test_MxpObzWr3eodJNxsEXG75M3S'
    # STRIPE_PUBLISHABLE_KEY = 'pk_test_4RztaeVX0rKfAeAo0HYmbFTh' #old
    STRIPE_PUBLISHABLE_KEY = 'pk_test_NEKutnAzZYYIhpzWZZ3DHu7B'


    braintree.Configuration.configure(
        braintree.Environment.Sandbox,
        "xjhkhxpc3dbc294q",
        "xrzqm4fpnc2rbwp5",
        "c31292311d69d7236258460b5edcf900"
        # 'xjhkhxpc3dbc294q',
        # 'zdngy2qzjnj5dyyz',
        # '315b62fc58325a22504954350425a970'
    )

    BRAINTREE_CSE = 'MIIBCgKCAQEA3pRTFuw5sbYLWsYz0us5YXW5/n46tHoJ7u+bOi8yEgCbijScOn/fVrmupT7C1kRAVBpmFDMBWLcek7QDQbwXw2602tYVxp55IR/KeUpu/zFVisi3Ne9HvNImkf7M1s3mcNCsdUBe5EM9y97kPmwFLrtnZbo092IqMkSEZfYslkNIVO55nX/RhXwf0UxVHYz7F1VdJTxTMWRiYLedP/Tg1IurSJqS5OmMkOcaZxVBQX/FkIRlMDL2OP18NFXaz1qQRRPRpqlCeyVZ2xzOT5Fjn4N7YqZa3HUl6XQYv1u3vso2Y8Uo2wN4CHqMBX/ddaf9mq11TWs6p5xLNt+9by/4/QIDAQAB'

    # TWILIO_ACCOUNT_SID = 'AC9b2f8a2ab7fe0766cf19aa7300544ea9'
    # TWILIO_AUTH_TOKEN = '040cb2ee1955ed284845350d025402ce'
    # TWILIO_NUMBER = '+15005550006'
    # temporarily use production settings during testing
    TWILIO_ACCOUNT_SID = 'AC7242ebfcde00fd2948a376f24f46545e'
    TWILIO_AUTH_TOKEN = '609ff14084378dd39d8220efa37e30aa'
    TWILIO_NUMBER = '+18329254818'
    # the only way to kick a braintree transaction from "submitted for settlement" to "settlement" in the
    # test environments is to manually push it there.  So we have to build a harness to do so that should
    # not be accessible in production
    USE_TRANSACTION_HARNESS = True

if PRODUCTION:
    # STRIPE_API_KEY = 'sk_live_4RztxvO6P6KBStYLGwtIl32j'
    # STRIPE_PUBLISHABLE_KEY = 'pk_live_4RzthcBayZ2uDVjI0AUz5Cwg'

    STRIPE_API_KEY = 'sk_live_3IDrwjgX6v14xrACYB8YxYQX'
    STRIPE_PUBLISHABLE_KEY = 'pk_live_bA7m6kU9zkgZzOmyjuPq2lPB'

    # braintree.Configuration.configure(
    #     braintree.Environment.Production,
    #     '2fssjvw2vzcttnsm',
    #     'h9hkxbm2djhdz2gv',
    #     'efd31246ee77c13c63d6c4b527786ac7'
    # )
    braintree.Configuration.configure(
        braintree.Environment.Production,
        "2fssjvw2vzcttnsm",
        "f9hx2fzd8r3k9dyw",
        "5b48dd1fb9fdec9c2521fef0ae75e511"
    )
    BRAINTREE_CSE = 'MIIBCgKCAQEAsnZf5kRrDj8dvvAnRIVBrhrlL4ZmyLIqunD5IFcCVEsA+NncxvH9kyNq3BHtKwHXF8esmjlDPL3hj42vjVvbhpGzAt0ocOV29ioC4KN9SzLBku7NUJzlBl92JFhkp7Y2AoyzLiWeOvW7U75bCMluhNQtWRvBtAGJi/bUAgGfiuELlq7kPYKLufYbDGGNNdLPmuJdsNB4P79NRUbssTh0wBZVijt9dSNjHEKDbo/7cwCwnnUv1luZSeLSrCIFJ98wrAB9yIIQvNBTXdgcKhYNlmGJbr25W8VGLnfLUsSA5sd9JLiIjk5OpNbO5tDW8XHtZRK0zFBJmprY0IiavP2cjwIDAQAB'

    TWILIO_ACCOUNT_SID = 'AC7242ebfcde00fd2948a376f24f46545e'
    TWILIO_AUTH_TOKEN = '609ff14084378dd39d8220efa37e30aa'
    TWILIO_NUMBER = '+18329254818'
    # NEVER set the below to True in production; it is for Braintree test transaction harness only
    USE_TRANSACTION_HARNESS = False

MAILCHIMP_API_KEY = 'c2082bdc782d4970674be9c2b4c8f215-us8'

DEFAULT_FROM_EMAIL = 'Rise <members@iflyrise.com>'
ANYWHERE_FROM_EMAIL ='Rise <anywhere@iflyrise.com>'

if DEBUG or STAGING or DEV:
    EMAIL_HOST = 'mailtrap.io'
    #EMAIL_HOST_USER = '55545a27baf50524b'
    #EMAIL_HOST_PASSWORD = '77a73bdaf4a429'
    #EMAIL_HOST_USER = '56385d2a4a5a816a3'  #anye
    #EMAIL_HOST_PASSWORD = '98cfeaac59970e' #anye
    #EMAIL_HOST_USER = '57740319eea041567' #greg
    #EMAIL_HOST_PASSWORD = '711940894064ce' #greg
    #EMAIL_HOST_USER = '80ee937350cacd' #sridhar
    #EMAIL_HOST_PASSWORD = '98ec03601efb0e' #sridhar
    EMAIL_HOST_USER = 'f7ddce24686190' #nick@iflyrise.com / riseisthebest
    EMAIL_HOST_PASSWORD = 'e01936f24d6045' #nick@iflyrise.com / riseisthebest

    EMAIL_PORT = '2525'
    EMAIL_USE_TLS = True
    #EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    PROTOCOL = 'http'

if PRODUCTION:
    EMAIL_HOST = 'smtp.sendgrid.net'
    EMAIL_HOST_USER = 'smtp-sendgrid'
    EMAIL_HOST_PASSWORD = 'CA3kxE6PSPjw!nG@N'
    EMAIL_PORT = '587'
    EMAIL_USE_TLS = True
    PROTOCOL = 'https'

# Redis
if DEBUG or STAGING or DEV:
    REDIS_URL = 'redis://localhost/0'

    # Celery Settings
    BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL

if PRODUCTION:
    REDIS_URL = 'redis://10.208.229.241/0'

    # Celery Settings
    BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL


if not STAGING and not PRODUCTION and not DEV:
    CELERY_ALWAYS_EAGER = True
    CELERY_EAGER_PROPAGATES_EXCEPTIONS = True


INFUSION_API_URL = 'https://hm206.infusionsoft.com:443/api/xmlrpc'
INFUSION_API_KEY = '269143ed7d1c3ed95537e54440e04bff'

# Application definition
INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'formtools',
    'raven.contrib.django.raven_compat',
    'cumulus',
    'import_export',
    'auditlog',
    'accounts',
    'account_profile',
    'dashboard',
    'billing',
    'flights',
    'anywhere',
    'reservations',
    'staticstorage',
    #'debug_toolbar.apps.DebugToolbarConfig',
    'imagekit',
    'rise',
    'htmlmailer',
    'support',
    'announcements',
    'reports',
    'core',
)


MIDDLEWARE_CLASSES = (
    'sslify.middleware.SSLifyMiddleware',
    # 'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'auditlog.middleware.AuditlogMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
    'rise.context_processors.context_settings',
)

ROOT_URLCONF = 'rise.urls'

WSGI_APPLICATION = 'rise.wsgi.application'

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases
if PRODUCTION:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'rise',
            'USER': 'rise',
            'PASSWORD': '9tDTwMPX47kA9kFejrCrLQpmPpiLjR',
            'HOST': '34cfffdd769245191733499e2f48d880e5f3ff52.rackspaceclouddb.com'
        }
    }

    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
            'LOCATION': [
                '10.208.229.241:11211',  # web01
                '10.208.233.255:11211',  # web02
            ],
            'TIMEOUT': None,  # default timeout of 24 hours
        }
    }

if STAGING:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'staging',
            'USER': 'staging',
            'PASSWORD': 'Bgyw7BPHJaeYtdhu22mQtDG2EWLRjK',
            'HOST': '34cfffdd769245191733499e2f48d880e5f3ff52.rackspaceclouddb.com'
        }
    }

    CACHES = {
        'default': {
            'BACKEND':  'django.core.cache.backends.memcached.PyLibMCCache',
            'LOCATION': [
                '127.0.0.1:11211',
            ],
            'TIMEOUT': None,  # default timeout of 24 hours
        }
    }

if DEV:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'dev',
            'USER': 'dev',
            'PASSWORD': 'riseisthebest',
            'HOST': '34cfffdd769245191733499e2f48d880e5f3ff52.rackspaceclouddb.com'
        }
    }

    CACHES = {
        'default': {
            'BACKEND':  'django.core.cache.backends.memcached.PyLibMCCache',
            'LOCATION': [
                '127.0.0.1:11211',
            ],
            'TIMEOUT': None,  # default timeout of 24 hours
        }
    }

if DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'rise',
            'USER': 'rise',
            'PASSWORD': '9Tp96sPuicNDuM2yFqoHcRRtXkFNCh',
        }
    }

    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
            'LOCATION': [
                '127.0.0.1:11211',
            ],
            'TIMEOUT': None,  # default timeout of 24 hours
        }
    }

    REDIS = 'redis://localhost:6379/0'

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'US/Central'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, 'static_collected')
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)

STATIC_ATTACHMENT_DIR = os.path.join(BASE_DIR, 'static')

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

CUMULUS = {
    'USERNAME': 'modifly.devs',
    'API_KEY': '76d6bf5b107e4fa29342de14a04358c0',
    'PYRAX_IDENTITY_TYPE': 'rackspace',
    'SERVICENET': PRODUCTION or STAGING or DEV,
    'USE_SSL': True,
    'HEADERS': (
        (r'.*\.(eot|otf|woff|ttf|woff2|svg)$', {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Expose-Headers': 'Access-Control-Allow-Origin'
        }),
    )
}

DEFAULT_MAILER_CONTEXT = {}

WP_URL = 'http://iflyrise.com'
TYPEKIT_URL = '//use.typekit.net/gja3gww.js'

if PRODUCTION:
    CUMULUS['CONTAINER'] = 'prod-media'
    CUMULUS['STATIC_CONTAINER'] = 'prod-static'
    STATIC_URL = 'https://cfa084d658b491813884-326c6674e44e477b9197a3210586152e.ssl.cf1.rackcdn.com/'
    MEDIA_URL = 'https://21fd10b8aee4451c7ef8-d9b52dc37146dbe99bbd8564f8ede29e.ssl.cf1.rackcdn.com/'

if STAGING:
    CUMULUS['CONTAINER'] = 'stag-media'
    CUMULUS['STATIC_CONTAINER'] = 'stag-static'
    STATIC_URL = 'https://75bf1d2fbfaaf67b5955-2630cff19e2e335859d29eaddeff077a.ssl.cf1.rackcdn.com/'
    MEDIA_URL = 'https://47b5232b8575911313c3-59d81109435a20e5738395836e330154.ssl.cf1.rackcdn.com/'
    WP_URL = 'http://flyrise.wpengine.com'

if DEV:
    CUMULUS['CONTAINER'] = 'dev-media'
    CUMULUS['STATIC_CONTAINER'] = 'dev-static'
    STATIC_URL = 'https://8681fb21743ecf9c0b70-d46384989e1811fa1572be6353586d3a.ssl.cf1.rackcdn.com/'
    MEDIA_URL = 'https://f370fe6d194e45f0ced9-0ebdc7af36dc51a14c14f1ecc34cb05b.ssl.cf1.rackcdn.com/'
    WP_URL = 'http://flyrise.wpengine.com'

if PRODUCTION or STAGING or DEV:
    DEFAULT_FILE_STORAGE = 'cumulus.storage.SwiftclientStorage'
    STATICFILES_STORAGE = 'staticstorage.storage.SwiftclientCachedStaticStorage'
    DEFAULT_AVATAR = '%simg/icon-default-user.png' % STATIC_URL

if DEBUG:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.CachedStaticFilesStorage'
    STATIC_URL = '/static/'
    MEDIA_URL = '/media/'
    DEFAULT_AVATAR = 'https://75bf1d2fbfaaf67b5955-2630cff19e2e335859d29eaddeff077a.ssl.cf1.rackcdn.com/img/icon-default-user.png'
    WP_URL = 'http://flyrise.WPEngine.com'

if PRODUCTION:
    RAVEN_CONFIG = {
        'dsn': 'https://8825e89e3fa942ada5335c61a98e284c:2e2f292fa9ae40b7bd2a2e484eceec5b@sentry.iflyrise.com/2',
    }

if STAGING:
    RAVEN_CONFIG = {
        'dsn': 'https://8eef9fe4c792420486220bbd440c0b18:0ba53473fd044c16b1beb91d1442f77e@sentry.iflyrise.com/3',
    }

if DEV:
    RAVEN_CONFIG = {
        'dsn': 'https://3f97ed2b337d43a1b3de543debf21604:873a87af701b43ee896cc96f23ca226d@sentry.iflyrise.com/4',
    }

# a mailchimp list where users are put after filling in the sign up form, but before paying
MAILCHIMP_LIMBO_LIST_ID = 'bfb3e941ee'
MAILCHIMP_WAITLIST_LIST_ID = '4396e3347c'
MAILCHIMP_UPDATES_LIST_ID = 'ee4e51aded'
MAILCHIMP_RISE_MEMBERS_LIST_ID = '22599db61a'
MAILCHIMP_ANYWHERE_MEMBERS_LIST_ID = '90b6f7c84a'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

PASS_COST = 750
COMPANION_PASS_COST = 750
COMPANION_PASS_COST_ROUND_TRIP = COMPANION_PASS_COST * 2
DEPOSIT_COST = 750

from decimal import Decimal
FET_TAX = Decimal('0.075')
DEPOSIT_TAX = Decimal('0.0825')
DEPOSIT_TAX_PERCENT = '8.25%'


if DEBUG or STAGING or DEV:
    SSLIFY_DISABLE = True


DEFAULT_MAILER_CONTEXT.update({
    'WP_URL': WP_URL,
    'TYPEKIT_URL': TYPEKIT_URL
})


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue'
        }
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'standard': {
            'format': '%(levelname)s %(asctime)s %(module)s %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'WARN',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'filters': ['require_debug_true'],
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'sentry': {
            'level': 'ERROR',
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console', 'sentry'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    }
}

SIGNUP_NOTIFICATION_LIST = ['info@iflyrise.com', 'nick@iflyrise.com', 'teresa@iflyrise.com','megan@iflyrise.com','joe.nageotte@iflyrise.com' ]
ANYWHERE_SIGNUP_NOTIFICATION_LIST = ['anywhere@iflyrise.com']
MANUAL_PAYMENT_NOTIFICATION_LIST = ['teresa@iflyrise.com']
ANYWHERE_REFUND_ERROR_NOTIFICATION_LIST = ['ops@iflyrise.com','teresa@iflyrise.com']
PAYMENT_FAILED_NOTIFICATION_LIST=['teresa@iflyrise.com','support@iflyrise.com']
WAITLIST_NOTIFICATION_LIST = ['ops@iflyrise.com', 'members@iflyrise.com']

DEFAULT_MORNING_TAKEOFF='09:00:00'
DEFAULT_AFTERNOON_TAKEOFF='16:00:00'
DEFAULT_EVENING_TAKEOFF='19:00:00'
DEFAULT_FLEXIBLE_TAKEOFF='11:00:00'

#Include <creator> tag in this subject to substitute the flight creator's name.
ANYWHERE_INVITATION_SUBJECT='Rise Flight Invitation from <creator>'

#this is set to 100 until the pager styling is fixed so we can see more of the flights
ANYWHERE_LANDING_PAGE_LIST_PAGESIZE = 4
DASHBOARD_ANYWHERE_LIST_PAGESIZE = 4


RISE_ANYWHERE_REQUEST_GROUPS = []

PARDOT_WEB_SIGNUP_URL = 'http://go.iflyrise.com/l/128951/2016-02-11/5grbx'

PARDOT_WEB_REFERRAL_URL = 'http://go.iflyrise.com/l/128951/2016-02-11/5grf6'

PARDOT_ANYWHERE_WEB_SIGNUP_URL = 'http://go.iflyrise.com/l/128951/2016-02-11/5grbz'

PARDOT_NOTIFY_WAIT_LIST = 'http://go.iflyrise.com/l/128951/2016-03-23/c47hp'

PARDOT_LANDING_LIST = 'http://go.iflyrise.com/l/128951/2016-03-24/c4v2p'

CLOUDSPONGE_KEY = '2882bb305d8f515dbdc90c8a4c5d1e67043a94cd'

FACEBOOK_SHARE_LINK_TITLE = "You\\'re Invited to Join My RISE ANYWHERE Flight"

ANYWHERE_FLIGHT_REQUEST_NOTIFICATION = ['ops@iflyrise.com', 'anywhere@iflyrise.com' ]

if PRODUCTION:
    CLOUDSPONGE_URI = "https://cfa084d658b491813884-326c6674e44e477b9197a3210586152e.ssl.cf1.rackcdn.com/css/cloudsponge.css"
if STAGING or DEV:
    CLOUDSPONGE_URI = "https://75bf1d2fbfaaf67b5955-2630cff19e2e335859d29eaddeff077a.ssl.cf1.rackcdn.com/css/cloudsponge.css"
if DEBUG:
    CLOUDSPONGE_URI = "http://127.0.0.1:8000/static/css/cloudsponge.css"

if PRODUCTION:
    LOAD_AVATARS=True
if STAGING or DEV:
    LOAD_AVATARS=True
if DEBUG:
    # change this to false if you are working against a prod backup.  Then use the load_avatars() account tag anywhere
    # you have failures due to avatars not loading.  This has only thus far been implemented on RISEAdmin User list.
    LOAD_AVATARS=True


# PRICING PARAMETERS
RISE_MARGIN = Decimal(0.3)
ONE_WAY_COST_MULTIPLIER = Decimal(1.0)
SHORT_TURN_TIME_HRS = int(48)
SHORT_TURN_COST_MULTIPLIER = Decimal(1.2)
LONG_TURN_COST_MULTIPLIER = Decimal(1.5)
CANCELLATION_WINDOW_ENDTIME=24

FLIGHT_ALERT_SUBJECT_24_HOURS = "Your RISE Flight Tomorrow"
FLIGHT_ALERT_SUBJECT_1_HOUR = "Your RISE Flight is Departing Soon"
GOOGLE_MAP_URL = "https://www.google.com/maps/place/"
GOOGLE_URL_SHORTNER = "https://www.googleapis.com/urlshortener/v1/url?key=AIzaSyCAXjpwobexlXnJYAmcemfuTNV_-YJ0iDQ"

# number of days to look back on for penalties
NO_SHOW_PENALTY_ASSESSMENT_DAYS = 90
# number of days a user will be restricted
NO_SHOW_PENALTY_DAYS=5

SYSTEM_ADMIN_EMAIL="sysadmin@iflyrise.com"

RESERVATION_EXPORT_DATE="01/01/16"
