#!/usr/bin/env python3

import aws_cdk as cdk

from cdk_test.cdk_test_stack import CdkTestStack


app = cdk.App()
CdkTestStack(app, "cdk-test")

app.synth()
