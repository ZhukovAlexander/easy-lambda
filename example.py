from lambdify import Lambda


@Lambda(name='echo')
def echo(*args, **kwargs):
    return args, kwargs
