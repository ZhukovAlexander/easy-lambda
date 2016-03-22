from deployment import Lambda


@Lambda(name='echo', bucket='olzhukovtest', key='test', role='arn:aws:iam::461318818653:role/lambda_s3_exec_role')
def echo(event, context):
    return event
