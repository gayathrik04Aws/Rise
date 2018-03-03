from django.contrib.staticfiles.storage import CachedFilesMixin
from django.utils.functional import cached_property
from cumulus.storage import SwiftclientStaticStorage


class SwiftclientCachedStaticStorage(CachedFilesMixin, SwiftclientStaticStorage):

    def get_available_name(self, name):
        """
        Returns a filename that's free on the target storage system, and
        available for new content to be written to.
        """
        return name

    def delete(self, name):
        """
        Skip deleting files, just overwrite them
        """
        pass

    @cached_property
    def all_files(self):
        """
        returns a dictionary of object name keys with the object values
        """
        objects = self.container.list_all()
        values = [(obj.name, obj) for obj in objects]
        objects = dict(values)
        return objects

    def exists(self, name):
        """
        Returns True if a file referenced by the given name already
        exists in the storage system, or False if the name is
        available for a new file.
        """
        return name in self.all_files

    def etag(self, name):
        """
        Returns the remote storage etag value for the given file for comparison or None if not found
        """
        if name in self.all_files:
            return self.all_files.get(name).hash
        return None

    def file_hash(self, name, content=None):
        """
        Retuns a hash of the file with the given name and optional content.
        """
        etag = self.etag(name)

        if etag is not None:
            return etag[:12]

        return super(SwiftclientCachedStaticStorage, self).file_hash(name, content)
