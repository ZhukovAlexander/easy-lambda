from lambdify import Lambda


@Lambda(name='echo')
def echo(event, context):
    return event
