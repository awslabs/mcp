#!/usr/bin/env python3
import aws_cdk as cdk
from basic_runtime_stack import AgentCoreRuntimeStack

app = cdk.App()
AgentCoreRuntimeStack(app, "BasicAgent")

app.synth()
