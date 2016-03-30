import boto3

from decorators import Lambda

iam = boto3.client('iam')
role = iam.get_role(RoleName='lambda_s3_exec_role')


@Lambda(name='echo', role=role['Role']['Arn'])
def echo(event, context):
    return event
