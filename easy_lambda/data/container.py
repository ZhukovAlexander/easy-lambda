import os
import dill

with open('.lambda.dump') as serialized:
    lambda_handler = dill.load(serialized)
