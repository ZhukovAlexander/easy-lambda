import os
import zipfile


class DeploymentPackage(object):
    def __init__(self, lambda_function, path=None):
        self.lambda_function = lambda_function
        if path:
            self.env_cache = path
        else:
            default = '/tmp/easy_lambda'
            if not os.path.isdir(default):
                os.mkdir(default)
            self.env_cache = '{}/{}.cache'.format(default, lambda_function.name)

    def copy_env(self, destination, venv_path=None):
        """
        Compies a python environment to the specified destination zip

        :param destination
        :type destination zipfile.ZipFile
        :param venv_path path to the virtualenv root
        :type venv_path str
        """

        venv = venv_path or os.environ['VIRTUAL_ENV']

        site_packages = os.path.join(venv, 'lib', 'python2.7', 'site-packages')

        def take_pyc(root_dir):
            # If there is a .pyc file in this package,
            # we can skip the python source code as we'll just
            # use the compiled bytecode anyway.
            return lambda f_name: not (
                f_name.endswith('.py') and os.path.isfile(os.path.join(root_dir, f_name) + 'c')
            )

        for root, dirs, files in os.walk(site_packages):
            for filename in filter(take_pyc(root), files):
                destination.write(
                        os.path.join(root, filename),
                        os.path.join(os.path.relpath(root, site_packages), filename)
                )

    def get_zipped_env(self):
        if not os.path.isfile(self.env_cache):
            with zipfile.ZipFile(self.env_cache, 'w', zipfile.ZIP_DEFLATED) as archive:
                path = os.path.join(os.path.dirname(__file__), 'data')
                for filename in os.listdir(path):
                    archive.write(os.path.join(path, filename), filename)

                # package your environment
                self.copy_env(archive)

        return zipfile.ZipFile(self.env_cache, 'a', zipfile.ZIP_DEFLATED)

    def zip_bytes(self, lambda_code):
        archive = self.get_zipped_env()

        # add serialized lambda function
        # make sure to add correct permissions
        # <http://stackoverflow.com/a/434689/2183102>
        info = zipfile.ZipInfo('.lambda.dump')
        info.external_attr = 0777 << 16L  # give full access to included file
        archive.writestr(info, lambda_code)
        archive.close()
        return open(self.env_cache).read()

