from decorators import Lambda

role = raw_input('Enter role ARN:')

# @Lambda(name='echo', role='arn:aws:iam::461318818653:role/lambda_s3_exec_role')


@Lambda(name='echo', role=role)
def echo(event, context):
    return event
