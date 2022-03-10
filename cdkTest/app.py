#!/usr/bin/env python3

from aws_cdk import (
    App
)
import os
from cdk_test.cdk_test_stack import CdkTestStack

app = App()
CdkTestStack(app, "cdk-test", env={
    'account': os.environ['CDK_DEFAULT_ACCOUNT'],
    'region': os.environ['CDK_DEFAULT_REGION']
  })

app.synth()
