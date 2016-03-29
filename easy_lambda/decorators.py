import json
import functools

import boto3
import dill

from deployment import DeploymentPackage

dill.settings['recurse'] = True


class LambdaProxy(object):

    def __init__(self, lambda_instance, client):
        self.client = client
        self.lambda_instance = lambda_instance

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

        return response

    def get(self):
        return self.client.get_function(FunctionName=self.lambda_instance.name)

    def update(self):
        return self.client.update_function_code(
                FunctionName=self.lambda_instance.name,
                ZipFile=self.lambda_instance.package.zip_bytes(self.lambda_instance.dumped_code),
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
    def __init__(self, name='', role='', client=None, description='', vps_config=None, package=None):
        self.client = client or boto3.client('lambda', region_name='us-west-2')

        self.name = name
        self.role = role
        self.description = description
        self.vps_config = vps_config or {}
        self.package = package or DeploymentPackage(self)

        self.dumped_code = None

    def __call__(self, functor):
        self.functor = functor
        self.dumped_code = dill.dumps(functor)

        return functools.wraps(functor)(LambdaProxy(self, self.client))

    def serialize(self):
        return dill.dumps(self.functor)

    def serialize_to(self, f):
        return dill.dump(self.functor, f)