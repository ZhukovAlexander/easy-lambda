from lambdify import Lambda, UPDATE_EXPLICIT


@Lambda.f(name='echo')
def echo(*args, **kwargs):
    return args, kwargs
