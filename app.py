#!/usr/bin/env python3
import aws_cdk as cdk
from three_tier_app.three_tier_app_stack import ThreeTierAppStack

app = cdk.App()
ThreeTierAppStack(app, "ThreeTierAppStack", env=cdk.Environment(account="123456789012", region="us-east-1"))
app.synth()

