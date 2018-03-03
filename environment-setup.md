# Environment Setup #

## About ##

The Rise codebase is hosted by github on https://github.com/Mobelux/Rise-Web. The current repository consists of a master branch and a teaser branch. The master branch is for the dynamic python/django site under development, and the teaser branch hosts the static teaser site.

## Setup Steps ##

These instructions are for Mac OS X.

### General Tools ###

1. Download and install Xcode: https://itunes.apple.com/us/app/xcode/id497799835?ls=1&mt=12
2. Install the Xcode command line tools: http://docwiki.embarcadero.com/RADStudio/XE4/en/Installing_the_Xcode_Command_Line_Tools_on_a_Mac
3. Verify ruby is installed by running `ruby -v` from the Terminal window.
4. Download and install Homebrew, a custom OS X package manager by running the command `ruby -e "$(curl -fsSL https://raw.github.com/Homebrew/homebrew/go/install)"` from the Terminal.
5. `brew install redis`
6. `brew install libmemcached`
7. `brew install memcached`
8. `sudo gem install sass`


### Tools for running Rise-Web


1. Doload and install github from this link: https://mac.github.com/
2. Run the github app.
3. Clone the Rise-Web repository, by selecting the plus icon in the github app on the upper left. A recommended location for where to put the repository is under a subfolder in your home directory, like "git/rise-web/". That way, from the Terminal, this can be easily accessed by `cd ~/git/rise-web`.
4. Python is pre-installed on OS X. Verify python is installed by opening a Terminal window and typing `python --version`. The output should display the version information for Python like `Python x.x.x`.
5. Download and install python's package manager, pip. From the terminal, try `sudo easy_install pip`. If that doesn't work, manually download and install the pip using the instructions in this link: http://pip.readthedocs.org/en/latest/installing.html.
6. Once pip is installed, open a Terminal window to install the virtual environment tool for Python by running this command: `sudo pip install virtualenv`.
7. Add the following snippet of bash code to your `.bash_profile`, then quit and restart your terminal:

``` bash
if [ `id -u` != '0' ]; then
  export VIRTUALENV_USE_DISTRIBUTE=1        # <-- Always use pip/distribute
  export WORKON_HOME=$HOME/.virtualenvs       # <-- Where all virtualenvs will be stored
  source /usr/local/bin/virtualenvwrapper.sh
  export PIP_VIRTUALENV_BASE=$WORKON_HOME
  export PIP_RESPECT_VIRTUALENV=true
fi
```

8. Once the virtual environment tools are set up, create a new virtual environment for Rise-Web.
use the command: virtualenv rise
http://docs.python-guide.org/en/latest/dev/virtualenvs/
9. Type `source rise/bin/activate` to switch to this virtual environment in the Terminal
10.. From this same Terminal, change directory to where the Rise-Web repository has been cloned on your local machine.
11. Run the pip command: `pip install -r requirements.txt` to install the required packages for Rise-Web.
12. Run the pip command: `pip install -r requirements_dev.txt` to install the required development packages for Rise-Web.




### Database setup Pt. 1

1. `brew install mysql`
2. Log into the mysql console `mysql -u root -p` (default root password is blank I believe).
3. Run the following commands to create the rise database and user with access to the rise database:

``` sql
CREATE DATABASE rise;

CREATE USER 'rise'@'localhost' IDENTIFIED BY '9Tp96sPuicNDuM2yFqoHcRRtXkFNCh';

GRANT ALL PRIVILEGES ON rise.* TO 'rise'@'localhost';

FLUSH PRIVILEGES;
```



### Sync media - this requires a rackspace account & private key, and will pull the staging database locally.
### (overwriting any local rise db you have!)
### You will get errors dealing with user accounts if you don't pull the media locally.
### Do this command from inside the rise-app directory.
fab staging sync_from_staging

1. Run the following django management command to create the initial database tables: `python manage.py syncdb`  (don't need to do this after sync_from_staging)
2. Run the following django management command to create the initial database tables that are under south's migration control: `python manage.py migrate`
3. Run `python manage.py createsuperuser` to create your admin user.



### Using the development environment

1. Start all the services by running `honcho start`. Honcho utilizes the `Procfile` to start processes for the django debug runserver and the sass compiler. There maybe future services that need to be run as well.
2. Once this development server loads on your local machine, navigate to [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in browser to view site.
3. Default admin is accessed via [http://127.0.0.1:8000/djangoadmin/](http://127.0.0.1:8000/djangoadmin/). Use the local superuser account credentials that you set previously to log in.

