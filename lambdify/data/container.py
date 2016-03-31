import os
import dill

with open('.lambda.dump', 'r') as serialized:
    lambda_handler = dill.load(serialized)
