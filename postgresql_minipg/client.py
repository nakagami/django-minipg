import subprocess

try:
    from django.db.backends import BaseDatabaseClient
except ImportError: # 1.8
    from django.db.backends.base.client import BaseDatabaseClient


class DatabaseClient(BaseDatabaseClient):
    executable_name = 'psql'

    def runshell(self):
        settings_dict = self.connection.settings_dict
        args = [self.executable_name]
        if settings_dict['USER']:
            args += ["-U", settings_dict['USER']]
        if settings_dict['HOST']:
            args.extend(["-h", settings_dict['HOST']])
        if settings_dict['PORT']:
            args.extend(["-p", str(settings_dict['PORT'])])
        args += [settings_dict['NAME']]
        subprocess.call(args)
