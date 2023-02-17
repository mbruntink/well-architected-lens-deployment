from constructs import Construct
from aws_cdk import (
    Stage
)
from .lens_stack import LensDeploymentStack

class LensDeploymentPipelineStage(Stage):

    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        service = LensDeploymentStack(self, 'LensDeployment')