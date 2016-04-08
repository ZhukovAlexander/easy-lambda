import json
import functools
from contextlib import contextmanager

import boto3
import botocore
import dill

from deployment import DeploymentPackage

dill.settings['recurse'] = True


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

    _context = None
    _inv_type = 'RequestResponse'

    version = '$LATEST'

    def __init__(self, func, name='', role='', description='', vps_config=None, package=None, flags=UPDATE_EXPLICIT):
        """
        Main Lambda constructor

        :param func: function to make an AWS Lambda from. This will be the actual lambda handler
        :param name:
        :param role: AWS role ARN
        :param description: function description
        :param vps_config: vps configuration
        :param package: deployment package for this function
        :param flags: this flags allow you to control the point in time, when to make an actual call to aws to create
        the function

        Usage:

        >>>from lambdify import Lambda
        >>>
        >>>func = Lambda(lambda x: x)
        >>>func.name
        '__main__.<lambda>'
        >>>func.create()
        {...}
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
        self._context = {}

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

        if self.create_options & UPDATE_ON_INIT == UPDATE_ON_INIT:
            self._create_or_update()

    @classmethod
    def f(cls, name='', role='', description='', vps_config=None, package=None, flags=UPDATE_EXPLICIT):
        """
        Alternative constructor factory to allow this class to be used as a decorator


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

    @contextmanager
    def call_context(self, version=None, inv_type=None, context=None):
        """Context managers, that allows the Lambda to be called with a
        specific version, context and invocation type

        :param  version: lambda function will use this version
        :param inv_type: invocation type
        :param context: lambda context

        >>>l = Lambda(lambda x: x, name='foo')
        >>>
        >>>with l.call_context(version='42', context={'bar': 'bar'}, inv_type='Event'):
        ...print l.version, l._context, l._inv_type
        ('42', {'bar': 'bar'}, 'Event')
        >>>
        >>>print l.version, l._context, l._inv_type
        ('$LATEST', {}, 'RequestResponse')

        """
        _version_orig, _inv_type_orig, _context_orig = self.version, self._inv_type, self._context.copy()
        try:
            self.version = version or self.version
            self._inv_type = inv_type or self._inv_type
            self._context = context or self._context
            yield
        finally:
            self.version, self._inv_type, self._context = _version_orig, _inv_type_orig, _context_orig

    def __call__(self, *args, **kwargs):
        kwargs.update({'args': args})
        resp = self.invoke(kwargs, self._context, version=self.version, inv_type=self._inv_type)
        return json.loads(resp['Payload'].read())

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
        response = self.client.create_function(
                FunctionName=self.name,
                Runtime='python2.7',
                Role=self.role,
                Handler='container.lambda_handler',
                Code={
                    'ZipFile': self.package.zip_bytes(self.dumped_code),

                },
                Description=self.description,
                Timeout=123,
                MemorySize=128,
                Publish=True,

        )

        return response

    def get(self, version=None):
        """Get the lambda instance details from AWS
        
        :param version: function version to get
        """
        return self.client.get_function(FunctionName=self.name, Qualifier=version or self.version)

    def update(self):
        """Update the lambda instance"""
        response = self.client.update_function_code(
                FunctionName=self.name,
                ZipFile=self.package.zip_bytes(self.dumped_code),
                # Publish=True|False
        )

        return response

    def invoke(self, event, context, inv_type=None, log_type='None', version=None):
        """Invoke the lambda function This is basically a low-level lambda interface.
        In most cases, you won't need to use this by yourself.

        :param event: lambda input
        :param context: lambda execution client context
        :param inv_type: invocation type
        :param log_type: log type
        :param version: version
        """
        if not self._was_updated and self.create_options & UPDATE_LAZY == UPDATE_LAZY:
            self._create_or_update()

        params = dict(
                FunctionName=self.name,
                InvocationType=inv_type or self._inv_type,
                LogType=log_type,
                ClientContext=json.dumps(context),
                Payload=json.dumps(event),
        )
        if version:
            params['Qualifier'] = version

        return self.client.invoke(**params)

    @property
    def versions(self):
        """List all versions for this Lambda"""
        return self.client.list_versions_by_function(FunctionName=self.name)['Versions']
