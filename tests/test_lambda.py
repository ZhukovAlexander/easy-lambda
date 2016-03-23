import unittest
import zipfile
from StringIO import StringIO
import tempfile
import shutil

import boto3
import dill
import moto
import mock
import pip

from easy_lambda.deployment import Lambda, DeploymentPackage


@moto.mock_lambda
class Test(unittest.TestCase):
    def setUp(self):
        super(Test, self).setUp()
        self.client = boto3.client('lambda', region_name='us-west-2')
    @mock.patch('easy_lambda.deployment.DeploymentPackage.copy_env')
    def test_create(self, mock):

        value = 1
        function_name = 'test_function'

        @Lambda(name=function_name, bucket='test', key='test', client=self.client)
        def foo():
            return value

        package = DeploymentPackage(foo)

        zfp = zipfile.ZipFile(StringIO(package.zip_bytes(foo.dumped_code)), "r")
        func = dill.load(zfp.open('.lambda.dump'))
        self.assertEqual(func(), value)

        resp_create = foo.create()
        self.assertEqual(resp_create['FunctionName'], function_name)

        # moto doesn't support ZipFile only lambda deployments, while
        # aws doen't allow other arguments when scpesifying ZipFile argument
        #resp_get = foo.get()
        #self.assertEqual(resp_get['Configuration']['FunctionName'], function_name)






@unittest.skip('slow')
class PackageTestCase(unittest.TestCase):

    def setUp(self):
        self.venv = tempfile.mkdtemp()
        #  <http://stackoverflow.com/a/19404371/2183102>
        pip.main(['install', 'requests', '-t', self.venv])
        shutil.copytree(self.venv, self.venv + '/lib/python2.7/site-packages')

    def test_copy_env(self):
        package = DeploymentPackage(None, None, None)
        with zipfile.ZipFile(StringIO(), 'w', zipfile.ZIP_DEFLATED) as dest:
            package.copy_env(dest, venv_path=self.venv)
            self.assertTrue(dest.namelist(), 'For now just test that it is not empty')

    def tearDown(self):
        shutil.rmtree(self.venv)

