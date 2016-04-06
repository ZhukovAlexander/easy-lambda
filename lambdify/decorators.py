import json
import functools

import boto3
import botocore
import dill

from deployment import DeploymentPackage

dill.settings['recurse'] = True


class LambdaProxy(object):
    def __init__(self, lambda_instance, client):
        self.client = client
        self.lambda_instance = lambda_instance

    def create(self):
        response = self.client.create_function(
                FunctionName=self.lambda_instance.name,
                Runtime='python2.7',
                Role=self.lambda_instance.role,
                Handler='container.lambda_handler',
                Code={
                    'ZipFile': self.lambda_instance.package.to_bytes(self.lambda_instance.dumped_code),
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
        response = self.client.update_function_code(
                FunctionName=self.lambda_instance.name,
                ZipFile=self.lambda_instance.package.zip_bytes(self.lambda_instance.dumped_code),
                # S3Bucket='string',
                # S3Key='string',
                # S3ObjectVersion='string',
                # Publish=True|False
        )

        return response

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


# this flags allow you to control the point in time at which to create/update your function
# It is needed due to the expensive transfer of a zip file with packed environment
# when updating/creating a function code
UPDATE_EXPLICIT = 0  # you'll have to create your lambda explicitly
UPDATE_ON_INIT = 1  # perform update on Lambda initialization
UPDATE_LAZY = 2  # perform update just before invoking the function
CREATE_ONCE = 4  # create the function, if it doesn't exist


class Lambda(object):
    """Wrapper class around a callable

    This wrapper basically replaces the original function with it's AWS Lambda instance.
    When called, the instance of this class will route the call to the AWS Instance, instead of
    calling a local function.
    


    """
    _was_updated = False

    def __init__(self, func, name='', role='', description='', vps_config=None, package=None, flags=UPDATE_EXPLICIT):
        """
        Main Lambda constructor

        >>>from lambdify import Lambda
        >>>
        >>>def echo(event):
        ...    return event
        >>>
        >>>echo = Lambda(echo, name='echo')
        >>>echo.create()



        :param func: function to make an AWS Lambda from. This will be the actual lambda handler
        :param name:
        :param role: AWS role ARN
        :param description: function description
        :param vps_config: vps configuration
        :param package: deployment package for this function
        :param flags: this flags allow you to control the point in time, when to make an actual call to aws to create
        the function
        """
        self.client = boto3.client('lambda', region_name='us-west-2')

        self.name = name or '{}.{}'.format(func.__module__, func.__name__)
        self.role = role
        if not role:
            iam = boto3.client('iam')
            role = iam.get_role(RoleName='lambda_s3_exec_role')
            self.role = role['Role']['Arn']

        self.description = description
        self.vps_config = vps_config or {}
        self.package = package or DeploymentPackage(self)
        self.create_options = flags

        # here we need to adapt the signature of the function to the AWS Lambda signature
        # according to https://docs.aws.amazon.com/lambda/latest/dg/python-programming-model-handler-types.html
        # TODO: allow different adapters. This will require changes to the  __call__ method
        @functools.wraps(func)
        def adapter(event, context):
            args = event.pop('args', [])
            return func(*args, **event)

        self.functor = adapter

        # serialize function early, otherwise dill could pick up global variable, not meant to be used
        # by this function
        self.dumped_code = dill.dumps(self.functor)

        self.proxy = LambdaProxy(self, self.client)

        if self.create_options & UPDATE_ON_INIT == UPDATE_ON_INIT:
            self._create_or_update()

    @classmethod
    def f(cls, name='', role='', description='', vps_config=None, package=None, flags=UPDATE_EXPLICIT):
        """
        Alternative constructor factory to allow this class to be used as a decorator

        >>>from lambdify import Lambda
        >>>@Lambda.f(name='echo')
        ...def echo(event):
        ...    return event
        ...
        >>>echo.create()


        :param name: lambda function name
        :param role: role ARN
        :param description: function description
        :param vps_config: vps configuration
        :param package: deployment package for this function
        :param flags: this flags allow you to control the point in time, when to make an actual call to aws to create
        the function
        :return: function decorator
        """

        def initialize(func):
            return cls(func,
                       name=name,
                       role=role,
                       description=description,
                       vps_config=vps_config,
                       package=package,
                       flags=flags)

        return initialize

    def __call__(self, *args, **kwargs):
        """Proxies calls to the wrapped callable instance to the actual cloud lambda.
        Note the signature of this method allows you to call it as a casual python function.
        Arguments will be automatically adapted to the (event, context) pair of argument, as required for
        lambda handler.
        """
        kwargs.update({'args': args})
        return json.loads(self.proxy.invoke(kwargs, None)['Payload'].read())

    def _create_or_update(self):
        try:
            self.get()
            self.update()
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                self.create()
            else:
                raise

        self._was_updated = True

    def create(self):
        """Create lambda function in AWS"""
        return self.proxy.create()

    def get(self):
        """Get the lambda instance details from AWS"""
        return self.proxy.get()

    def update(self):
        """Update the lambda instance"""
        return self.proxy.update()

    def invoke(self, event, context):
        """Invoke the lambda function.
        """
        if not self._was_updated and self.create_options & UPDATE_LAZY == UPDATE_LAZY:
            self._create_or_update()
        return self.proxy.invoke(event, context)

    def _serialize(self):
        return dill.dumps(self.functor)

    def _serialize_to(self, f):
        return dill.dump(self.functor, f)
