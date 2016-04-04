# λambdify - feel yourserlf like an AWS Lambda God

**lambdify** allows you to create AWS Lambda function directly from the python code.
Just like that:

install *lambdify*...
```bash
$pip install lambdify
```
...create AWS Lambda with 4 lines of code:
```python
from lambdify import Lambda


@Lambda.f(name='echo')
def echo(*args, **kwargs):
    return args, kwargs


if __name__ == '__main__':
    import getpass
    echo(msg='Hello, {user}!'.format(user=getpass.getuser()))
```

Now you can head over to your [AWS Lambda console](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions/echo) and behold your **echo** function

* No more bothering packaging your env
* [Celery](http://docs.celeryproject.org/en/latest/userguide/tasks.html#basics)-like function definition
