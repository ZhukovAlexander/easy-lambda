import json
import os
import tempfile
import zipfile
from StringIO import StringIO
import time
import shutil

import dill
import boto3


class DeploymentPackage(object):
    def __init__(self, lambda_function):
        self.lambda_function = lambda_function

    def copy_env(self, destination, venv_path=None):
        """
        Compies a python environment to the specified destination zip

        :param destination
        :type destination zipfile.ZipFile
        :param venv_path path to the virtualenv root
        :type venv_path str
        """

        venv = venv_path or os.environ['VIRTUAL_ENV']

        package_path = tempfile.mkdtemp()
        package_path = os.path.join(tempfile.gettempdir(), str(int(time.time() + 1)))
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

                destination.write(os.path.join(root, filename), os.path.join(root.replace(venv, ''), filename))

    def zip_bytes(self, lambda_code):
        mf = StringIO()
        with zipfile.ZipFile(mf, 'w', zipfile.ZIP_DEFLATED) as archive:
            path = os.path.join(os.path.dirname(__file__), 'data')
            for filename in os.listdir(path):
                archive.write(os.path.join(path, filename), filename)
            # add serialized lambda function
            archive.writestr('.lambda.dump', lambda_code)
        return mf.getvalue()


class LambdaProxy(object):

    def __init__(self, lambda_object):
        self.lambda_object = lambda_object

    def create(self):
        return self.lambda_object.create()

    def get(self):
        return self.lambda_object.get()

    def __call__(self, event, context):
        return self.lambda_object.invoke(event, context)


class Lambda(object):
    def __init__(self, name='', role='', bucket='', key='', client=None, description='', vps_config=None):

        self.client = client or boto3.client('lambda', region_name='us-west-2')

        self.name = name
        self.role = role
        self.bucket = bucket
        self.key = key
        self.description = description
        self.vps_config = vps_config or {}

    def __call__(self, functor):
        self.functor = functor
        return self

    def serialize(self):
        return dill.dumps(self.functor)

    def serialize_to(self, f):
        return dill.dump(self.functor, f)

    def create(self):
        package = DeploymentPackage(self)
        response = self.client.create_function(
                FunctionName=self.name or self.functor.__name__,
                Runtime='python2.7',
                Role=self.role,
                Handler='container.lambda_handler',
                Code={
                    'ZipFile': package.zip_bytes(self.serialize()),
                    'S3Bucket': self.bucket,
                    'S3Key': self.key,
                    'S3ObjectVersion': 'string'
                },
                Description=self.description,
                Timeout=123,
                MemorySize=128,
                Publish=True,
                VpcConfig={
                    'SubnetIds': [
                        'string',
                    ],
                    'SecurityGroupIds': [
                        'string',
                    ]
                }
        )

        return response

    def get(self):
        return self.client.get_function(FunctionName=self.name)

    def invoke(self, event, context, inv_type='RequestResponse', log_type='None', version=None):
        params = dict(
            FunctionName=self.name,
            InvocationType=inv_type,
            LogType=log_type,
            # ClientContext='string',
            Payload=json.dumps(event),
        )
        if version:
            params['Qualifier'] = version

        return self.client.invoke(**params)
