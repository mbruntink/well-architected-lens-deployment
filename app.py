#!/usr/bin/env python3
import os

import aws_cdk as cdk

from stacks.lens_pipeline import LensPipeline

app = cdk.App()
LensPipeline(app, "WellArchitectedPipelineStack")
   
app.synth()
