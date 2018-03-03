from django.contrib.staticfiles.management.commands.collectstatic import Command as CollectStaticCommand
from pyrax.utils import get_checksum


class Command(CollectStaticCommand):

    def delete_file(self, path, prefixed_path, source_storage):
        """
        Compare files using hashes/etags vs modified time
        """
        if self.storage.exists(prefixed_path):
            full_local_path = source_storage.path(prefixed_path)
            local_etag = get_checksum(full_local_path)
            remote_etag = self.storage.etag(prefixed_path)

            if local_etag == remote_etag:
                if prefixed_path not in self.unmodified_files:
                    self.unmodified_files.append(prefixed_path)
                self.log("Skipping '%s' (not modified)" % path)
                return False

            # Then delete the existing file if really needed
            if self.dry_run:
                self.log("Pretending to delete '%s'" % path)
            else:
                self.log("Deleting '%s'" % path)
                self.storage.delete(prefixed_path)
        return True
