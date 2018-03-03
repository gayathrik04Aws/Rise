import os
from collections import OrderedDict

from django.conf import settings
from django.contrib.staticfiles.management.commands.collectstatic import Command as CollectStaticCommand
from django.core.management.color import no_style
from django.contrib.staticfiles.finders import get_finders

# TODO: probably do not need pyrax
"""
import pyrax
from pyrax.utils import get_checksum
pyrax.set_setting("identity_type", settings.CUMULUS["PYRAX_IDENTITY_TYPE"])
pyrax.set_credentials(settings.CUMULUS["USERNAME"], settings.CUMULUS["API_KEY"])
"""

from cumulus.storage import SwiftclientStorage
swiftclient_storage = SwiftclientStorage()

from cumulus.authentication import Auth
from cumulus.settings import CUMULUS
from cumulus.storage import get_headers, get_content_type, get_gzipped_contents


class Command(CollectStaticCommand):
    """
    Command that allows to copy or symlink media files from Rackspace Cloud
    Files location to the settings.MEDIA_ROOT.
    """
    help = "Collect media files in a single location."


    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.copied_files = []
        self.symlinked_files = []
        self.unmodified_files = []
        self.post_processed_files = []
        self.storage = swiftclient_storage
        self.style = no_style()
        try:
            self.storage.path('')
        except NotImplementedError:
            self.local = False
        else:
            self.local = True


    def set_options(self, **options):
        """
        Set instance variables based on an options dict
        """
        self.interactive = options['interactive']
        self.verbosity = options['verbosity']
        self.symlink = options['link']
        self.clear = options['clear']
        self.dry_run = options['dry_run']
        ignore_patterns = options['ignore_patterns']
        if options['use_default_ignore_patterns']:
            ignore_patterns += ['CVS', '.*', '*~']
        self.ignore_patterns = list(set(ignore_patterns))
        self.post_process = options['post_process']

        self.container_name = CUMULUS["CONTAINER"]

        self._connection = Auth()._get_connection()
        self.container = self._connection.get_container(self.container_name)



    def collect(self):
        """
        Perform the bulk of the work of collectstatic.

        Split off from handle() to facilitate testing.
        """
        if self.symlink and not self.local:
            raise CommandError("Can't symlink to a remote destination.")

        if self.clear:
            self.clear_dir('')

        if self.symlink:
            handler = self.link_file
        else:
            handler = self.copy_file

        cloud_objects = self.container.get_objects()

        for obj in cloud_objects:
            if self.dry_run:
                self.log("Pretending to copy '%s'" % obj.name, level=1)
            else:
                self.log("Copying '%s'" % obj.name, level=1)
                obj.download(settings.MEDIA_ROOT)

        # TODO: don't overwrite files with matching timestamps
        # TODO: delete local files that don't match any remote objects

        return {
            'modified': [obj.name for obj in cloud_objects],
            'unmodified': [],
            'post_processed': [],
        }
