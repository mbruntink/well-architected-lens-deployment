from constructs import Construct
from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_codecommit as codecommit,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_iam as iam
)

class LensDeploymentStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        repo = codecommit.Repository(self, 'LensRepo',
            repository_name='well-architected-lens',
        )     

        deployment_action_lambda = lambda_.Function(
            self,
            "LensDeploymentAction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset("assets/lens-deployment-codepipeline-action"),
            handler="app.handler",
        )

        deployment_action_lambda.role.add_to_principal_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "codecommit:GetFile",
                ],
                resources=[
                    repo.repository_arn
                ],
            )
        )

        deployment_action_lambda.role.add_to_principal_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "wellarchitected:ImportLens",
                    "wellarchitected:DeleteLens",
                    "wellarchitected:CreateLensShare",
                    "wellarchitected:CreateLensVersion",
                    "wellarchitected:DeleteLensShare",
                    "wellarchitected:GetLens",
                    "wellarchitected:GetLensVersion",
                    "wellarchitected:TagResource"
                ],
                resources=[
                    "*"
                ],
            )
        )

        deployment_action_lambda.role.add_to_principal_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "wellarchitected:ListLenses"
                ],
                resources=[
                    "arn:aws:wellarchitected:{}:{}:/lenses".format(self.region, self.account)
                ],
            )
        )

        # define the s3 artifact
        source = codepipeline.Artifact()
        
        source_action =  codepipeline_actions.CodeCommitSourceAction(
            repository=repo,
            branch='main',
            action_name='CodeCommit',
            output=source
        )
        # define the pipeline
        pipeline = codepipeline.Pipeline(
            self, "LensDeploymentPipeline",
            pipeline_name='well-architected-lens-deployment',
            stages=[
                codepipeline.StageProps(
                    stage_name='Source',
                    actions=[
                        source_action
                    ]
                ),
                codepipeline.StageProps(
                    stage_name='DeployLens',
                    actions=[
                        codepipeline_actions.LambdaInvokeAction(
                            lambda_=deployment_action_lambda,
                            action_name='PublishLens',
                            user_parameters={
                                'CommitId': source_action.variables.commit_id,
                                'Repo': source_action.variables.repository_name,
                                'Branch': source_action.variables.branch_name
                            }
                        )
                    ]
                )
            ]
        )