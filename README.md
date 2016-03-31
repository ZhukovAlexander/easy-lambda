# λambdify - feel yourserlf like an AWS Lambda God

**lambdify** allows you to create AWS Lambda function directly from the python code.
Just like that:
```python
from lambdify import Lambda


@Lambda(name='echo')
def echo(event, context):
    return event

if __name__ == '__main__':
    import getpass
    echo(msg='Hello, {user}!'.format(user=getpass.getuser()))
```
