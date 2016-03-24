import json
import os
import tempfile
import warnings
import zipfile
import functools

import dill

dill.settings['recurse'] = True

import boto3


class DeploymentPackage(object):
    def __init__(self, lambda_function, path=None):
        self.lambda_function = lambda_function
        self.env_cache = path or '/tmp/easy_lambda/{}.cache'.format(lambda_function.name)

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


class LambdaProxy(object):

    def __init__(self, lambda_instance, client):
        self.client = client
        self.lambda_instance = lambda_instance

    def __call__(self, *args, **kwargs):
        kwargs.update({'args': args})
        return json.loads(self.invoke(kwargs, None)['Payload'].read())

    def create(self):
        package = DeploymentPackage(self.lambda_instance)
        response = self.client.create_function(
                FunctionName=self.lambda_instance.name,
                Runtime='python2.7',
                Role=self.lambda_instance.role,
                Handler='container.lambda_handler',
                Code={
                    'ZipFile': package.zip_bytes(self.lambda_instance.dumped_code),
                    # 'S3Bucket': self.bucket,
                    # 'S3Key': self.key,
                    # 'S3ObjectVersion': 'string'
                },
                Description=self.lambda_instance.description,
                Timeout=123,
                MemorySize=128,
                Publish=True,

        )

        return response

    def get(self):
        return self.client.get_function(FunctionName=self.lambda_instance.name)

    def update(self):
        package = DeploymentPackage(self.lambda_instance)
        return self.client.update_function_code(
                FunctionName=self.lambda_instance.name,
                ZipFile=package.zip_bytes(self.lambda_instance.dumped_code),
                # S3Bucket='string',
                # S3Key='string',
                # S3ObjectVersion='string',
                # Publish=True|False
        )

    def invoke(self, event, context, inv_type='RequestResponse', log_type='None', version=None):
        params = dict(
                FunctionName=self.lambda_instance.name,
                InvocationType=inv_type,
                LogType=log_type,
                # ClientContext='string',
                Payload=json.dumps(event),
        )
        if version:
            params['Qualifier'] = version

        return self.client.invoke(**params)


class Lambda(object):
    def __init__(self, name='', role='', bucket='', key='', client=None, description='', vps_config=None):
        self.client = client or boto3.client('lambda', region_name='us-west-2')

        self.name = name
        self.role = role
        self.bucket = bucket
        self.key = key
        self.description = description
        self.vps_config = vps_config or {}

        self.dumped_code = None

    def __call__(self, functor):
        self.functor = functor
        self.dumped_code = dill.dumps(functor)

        return functools.wraps(functor)(LambdaProxy(self, self.client))

    def serialize(self):
        return dill.dumps(self.functor)

    def serialize_to(self, f):
        return dill.dump(self.functor, f)
