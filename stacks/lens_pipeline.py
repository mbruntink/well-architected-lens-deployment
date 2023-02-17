import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_codecommit as codecommit
)
from aws_cdk.pipelines import CodePipeline, CodePipelineSource, ShellStep
from stacks.lens_stage import LensDeploymentPipelineStage

class LensPipeline(Stack):

    def __init__(self, scope, construct_id, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        repo = codecommit.Repository(self, 'Repo',
            repository_name='well-architected-lens-stack',
        )

        pipeline = CodePipeline(self, 'LambdaPipeline',
            pipeline_name='well-architected-lens-stack-deployment',
            docker_enabled_for_synth=True,
            self_mutation=True,
            synth=ShellStep('Synth',
                input=CodePipelineSource.code_commit(  
                    repo, 'main'),
                    commands=[
                    'npm install -g aws-cdk',
                    'python -m pip install -r requirements.txt',
                    'cdk synth'
                ]
            )
        )

        deploy = LensDeploymentPipelineStage(self, "Deploy")
        deploy_stage = pipeline.add_stage(deploy)

