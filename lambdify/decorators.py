import json
import functools

import boto3
import botocore
import dill

from deployment import DeploymentPackage

dill.settings['recurse'] = True


class LambdaProxy(object):
    _updated = False

    def _create_or_update(self):
        try:
            self.get()
            self.update()
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                self.create()
            else:
                raise

    def __init__(self, lambda_instance, client):
        self.client = client
        self.lambda_instance = lambda_instance

        if self.lambda_instance.create_options & UPDATE_ON_INIT == UPDATE_ON_INIT:
            self._create_or_update()

    def __call__(self, *args, **kwargs):
        kwargs.update({'args': args})
        return json.loads(self.invoke(kwargs, None)['Payload'].read())

    def create(self):
        response = self.client.create_function(
                FunctionName=self.lambda_instance.name,
                Runtime='python2.7',
                Role=self.lambda_instance.role,
                Handler='container.lambda_handler',
                Code={
                    'ZipFile': self.lambda_instance.package.zip_bytes(self.lambda_instance.dumped_code),
                    # 'S3Bucket': self.bucket,
                    # 'S3Key': self.key,
                    # 'S3ObjectVersion': 'string'
                },
                Description=self.lambda_instance.description,
                Timeout=123,
                MemorySize=128,
                Publish=True,

        )
        self._updated = True

        return response

    def get(self):
        return self.client.get_function(FunctionName=self.lambda_instance.name)

    def update(self):
        response = self.client.update_function_code(
                FunctionName=self.lambda_instance.name,
                ZipFile=self.lambda_instance.package.zip_bytes(self.lambda_instance.dumped_code),
                # S3Bucket='string',
                # S3Key='string',
                # S3ObjectVersion='string',
                # Publish=True|False
        )

        self._updated = True

        return response

    def invoke(self, event, context, inv_type='RequestResponse', log_type='None', version=None):
        if not self._updated and self.lambda_instance.create_options & UPDATE_LAZY == UPDATE_LAZY:
            self._create_or_update()

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


# this flags allow you to control the point in time at which to create/update your function
# It is needed due to the expensive transfer of a zip file with packed environment
# when updating/creating a function code
UPDATE_EXPLICIT = 0  # you'll have to create your lambda explicitly
UPDATE_ON_INIT = 1  # perform update on Lambda initialization
UPDATE_LAZY = 2  # perform update just before invoking the function
CREATE_ONCE = 4  # create the function, if it doesn't exist


class Lambda(object):
    def __init__(self, name='', role='', description='', vps_config=None, package=None, flags=UPDATE_ON_INIT):
        self.client = boto3.client('lambda', region_name='us-west-2')

        self.name = name
        self.role = role
        self.description = description
        self.vps_config = vps_config or {}
        self.package = package or DeploymentPackage(self)
        self.create_options = flags

        self.dumped_code = None

    def __call__(self, functor):
        self.functor = functor

        self.dumped_code = dill.dumps(functor)
        self.name = self.name or '{}.{}'.format(self.functor.__module__, self.functor.__name__)

        return functools.wraps(functor)(LambdaProxy(self, self.client))

    def serialize(self):
        return dill.dumps(self.functor)

    def serialize_to(self, f):
        return dill.dump(self.functor, f)
