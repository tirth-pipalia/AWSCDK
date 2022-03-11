#!/usr/bin/env python3

from aws_cdk import (
    App
)
import aws_cdk as cdk
from cdk_test.cdk_test_stack import CdkTestStack

env_ME = cdk.Environment(account="12-digit-AccountNo", region="me-south-1")
app = App()
CdkTestStack(app, "cdk-test", env=env_ME)

app.synth()
