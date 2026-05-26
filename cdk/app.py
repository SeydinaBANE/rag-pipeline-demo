from __future__ import annotations

import os

import aws_cdk as cdk
from stacks.compute_stack import ComputeStack
from stacks.data_stack import DataStack
from stacks.security_stack import SecurityStack
from stacks.vpc_stack import VpcStack

app = cdk.App()

env = cdk.Environment(
    account=os.environ.get("CDK_ACCOUNT", os.environ.get("AWS_ACCOUNT_ID")),
    region=os.environ.get("CDK_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1")),
)

vpc_stack = VpcStack(app, "RagVpc", env=env)

data_stack = DataStack(app, "RagData", vpc=vpc_stack.vpc, env=env)
data_stack.add_dependency(vpc_stack)

security_stack = SecurityStack(app, "RagSecurity", env=env)

compute_stack = ComputeStack(
    app,
    "RagCompute",
    vpc=vpc_stack.vpc,
    data_stack=data_stack,
    security_stack=security_stack,
    env=env,
)
compute_stack.add_dependency(data_stack)
compute_stack.add_dependency(security_stack)

app.synth()
