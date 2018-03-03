from fabric.api import sudo, env, lcd, cd, local, shell_env, get, settings
from fabric.decorators import runs_once, parallel
import re

env.code_root = '/var/django/rise'
env.clear_cache = True


def runserver():
    local('python manage.py runserver 0.0.0.0:8000')


def debug():
    env.hosts = ['0.0.0.0:8000']
    env.shell_env = {'STAGING': 'False', 'PRODUCTION': 'False', 'DEV':'False'}


def staging():
    env.hosts = ['stage.iflyrise.com']
    env.shell_env = {'STAGING': 'True'}
    env.db = {
        'host': '34cfffdd769245191733499e2f48d880e5f3ff52.rackspaceclouddb.com',
        'port': 3306,
        'user': 'staging',
        'password': 'Bgyw7BPHJaeYtdhu22mQtDG2EWLRjK',
        'name': 'staging'

    }

def dev():
    env.hosts = ['dev.iflyrise.com']
    env.shell_env = {'DEV': 'True'}
    env.db = {
        'host': '34cfffdd769245191733499e2f48d880e5f3ff52.rackspaceclouddb.com',
        'port': 3306,
        'user': 'dev',
        'password': 'riseisthebest',
        'name': 'dev'

    }


def production():
    env.hosts = ['web01.iflyrise.com', 'web02.iflyrise.com']
    env.shell_env = {'PRODUCTION': 'True'}
    env.db = {
        'host': '34cfffdd769245191733499e2f48d880e5f3ff52.rackspaceclouddb.com',
        'port': 3306,
        'user': 'rise',
        'password': '9tDTwMPX47kA9kFejrCrLQpmPpiLjR',
        'name': 'rise'
    }


@parallel
def pull():
    "Push out new code to the server."
    with cd(env.code_root):
        sudo("git pull")


@parallel
def set_branch(branch_name):
    with cd(env.code_root):
        sudo('git checkout {}'.format(branch_name))


@runs_once
def collectstatic():
    with shell_env(**env.shell_env):
        with cd(env.code_root):
            sudo(
                '/var/virtualenvs/rise/bin/python manage.py collect_static --noinput --verbosity=2 --ignore="*.scss" --ignore="fonts*"',
                user='www-data')

# use this version when you add fonts!
# @runs_once
# def collectstatic():
#     with shell_env(**env.shell_env):
#         with cd(env.code_root):
#             sudo(
#                 '/var/virtualenvs/rise/bin/python manage.py collect_static --noinput --verbosity=2 --ignore="*.scss" ',
#                 user='www-data')


@runs_once
def migrate():
    with shell_env(**env.shell_env):
        with cd(env.code_root):
            sudo('/var/virtualenvs/rise/bin/python manage.py migrate')


@parallel
def reload():
    """
    Reload gunicorn to pick up new code changes.
    """
    sudo('find %s -name "*.pyc" -exec rm -rf {} \;' % (env.code_root,))
    sudo("shopt -s nullglob;for pid in /var/django/*.pid; do echo $pid; sudo kill -HUP `cat $pid`; done")
    sudo('supervisorctl restart worker')


@parallel
def update_requirements():
    """
    Update pip requirements
    """
    with shell_env(**env.shell_env):
        with cd(env.code_root):
            sudo('/var/virtualenvs/rise/bin/pip install -r requirements.txt')

@runs_once
def clear_cache():
    with shell_env(**env.shell_env):
        with cd(env.code_root):
            sudo('/var/virtualenvs/rise/bin/python manage.py clear_cache')


def deploy(skip_static=False):
    """
    skip_static allows skipping collect static files to speed up deployment of code only changes

    usage to skip static: fab <ENVIRONMENT> deploy:True
    usage to include collect static: fab <ENVIRONMENT> deploy
    """
    pull()
    update_requirements()
    migrate()
    if not skip_static:
        collectstatic()
    if env.clear_cache:
        clear_cache()
    reload()


@runs_once
def get_db(out_file=None):
    """
    Fetch remote DB to an SQL file in the local directory.

    :param out_file: filename to save DB as. defaults to <db_name>.sql
    """
    assert env.get('db'), 'no DB defined in env'

    if out_file is None:
        out_file = '{db[name]}.sql'.format(db=env.db)

    # simple check to prevent worst case rm -rf /
    assert not re.search(r'[/\\]', out_file), 'out_file path not allowed'

    with shell_env(**env.shell_env):
        with cd(env.code_root):
            sudo('mysqldump -P{db[port]} -h{db[host]} -p{db[password]} -u{db[user]} {db[name]} > {filename}'.format(
                db=env.db, filename=out_file
            ))
            local('scp {env.user}@{env.host_string}:{env.code_root}/{filename} {filename}'.format(
                env=env, filename=out_file
            ))
            sudo('rm {filename}'.format(filename=out_file))


def sync_from_staging():
    """
    Syncs both the database and media from staging
    """
    sync_from_staging_db()
    sync_staging_media()


def sync_from_dev():
    """
    Syncs both the database and media from staging
    """
    sync_from_dev_db()
    sync_dev_media()


def sync_from_staging_db():
    """
    Gets and imports the staging database
    """
    assert env.shell_env.get('STAGING'), 'Not executing in staging env'
    get_db('latest.sql')

    local('mysqladmin -u rise -p9Tp96sPuicNDuM2yFqoHcRRtXkFNCh -f drop rise')
    local('mysqladmin -u rise -p9Tp96sPuicNDuM2yFqoHcRRtXkFNCh create rise')
    with settings(warn_only=True):
        local('mysql -urise -p9Tp96sPuicNDuM2yFqoHcRRtXkFNCh rise < latest.sql')
    local('rm latest.sql')


def sync_from_dev_db():
    """
    Gets and imports the staging database
    """
    assert env.shell_env.get('DEV'), 'Not executing in dev env'
    get_db('latest.sql')

    local('mysqladmin -u rise -p9Tp96sPuicNDuM2yFqoHcRRtXkFNCh -f drop rise')
    local('mysqladmin -u rise -p9Tp96sPuicNDuM2yFqoHcRRtXkFNCh create rise')
    with settings(warn_only=True):
        local('mysql -urise -p9Tp96sPuicNDuM2yFqoHcRRtXkFNCh rise < latest.sql')
    local('rm latest.sql')


def sync_staging_media():
    """
    Downloads the staging media directory
    """
    with shell_env(**env.shell_env):
        with cd(env.code_root):
            local('mkdir -p rise/media/')
            sudo('mkdir -p rise/media/')
            sudo('/var/virtualenvs/rise/bin/python manage.py collect_media --noinput')
            download_media = 'scp -rp ' + env.user + '@' + env.hosts[
                0] + ':' + env.code_root + '/rise/media/ ./rise'  # fab changes to correct local dir apparently
            local(download_media)

def sync_dev_media():
    """
    Downloads the staging media directory
    """
    with shell_env(**env.shell_env):
        with cd(env.code_root):
            local('mkdir -p rise/media/')
            sudo('mkdir -p rise/media/')
            sudo('/var/virtualenvs/rise/bin/python manage.py collect_media --noinput')
            download_media = 'scp -rp ' + env.user + '@' + env.hosts[
                0] + ':' + env.code_root + '/rise/media/ ./rise'  # fab changes to correct local dir apparently
            local(download_media)


@runs_once
def sync_from_production():
    """
    Syncs both the database and media from production
    """
    sync_from_production_db()
    sync_production_media()


@runs_once
def sync_from_production_db():
    """
    Gets and imports the production database
    """
    assert env.shell_env.get('PRODUCTION'), 'Not executing in production env'

    get_db('latest.sql')

    local('mysqladmin -u rise -p9Tp96sPuicNDuM2yFqoHcRRtXkFNCh -f drop rise')
    local('mysqladmin -u rise -p9Tp96sPuicNDuM2yFqoHcRRtXkFNCh create rise')
    with settings(warn_only=True):
        local('mysql -urise -p9Tp96sPuicNDuM2yFqoHcRRtXkFNCh rise < latest.sql')
    local('rm latest.sql')


@runs_once
def sync_production_media():
    """
    Downloads the production media directory
    """
    with shell_env(**env.shell_env):
        with cd(env.code_root):
            local('mkdir -p rise/media/')
            sudo('mkdir -p rise/media/')
            sudo('/var/virtualenvs/rise/bin/python manage.py collect_media --noinput')
            download_media = 'scp -rp ' + env.user + '@' + env.hosts[
                0] + ':' + env.code_root + '/rise/media/ ./rise'  # fab changes to correct local dir apparently
            local(download_media)




def sync_from_remote_db():
    """
    Gets and imports the remote database
    TODO: get the project settings import to work
    """
    import os

    with lcd(os.path.abspath(__FILE__)):
        from fabric.contrib import django
        django.project('rise')
        # TODO: get DB info from settings file based on env. vars


def local_timezone_setup():
    local(
        'mysql_tzinfo_to_sql /usr/share/zoneinfo | sed -e "s/Local time zone must be set--see zic manual page/local/" | mysql -u root mysql')
