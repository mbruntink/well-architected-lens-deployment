import json
import boto3
import botocore
import logging
import os

codepipeline = boto3.client('codepipeline')
codecommit = boto3.client("codecommit")
wellarchitected = boto3.client('wellarchitected')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def put_job_success(job_id):
    codepipeline.put_job_success_result(
        jobId=job_id
    )

def put_job_failure(job_id, message, execution_id):
    codepipeline.put_job_failure_result(
        jobId=job_id,
        failureDetails={
            'message': message,
            'type': 'JobFailed',
            'externalExecutionId': execution_id
        }
    )

def handler(event, context):
   
    user_parameters = json.loads(event["CodePipeline.job"]['data']['actionConfiguration']['configuration']['UserParameters'])
    job_id = event['CodePipeline.job']['id']
    commit_id = user_parameters['CommitId']
    branch = user_parameters['Branch']
    repo = user_parameters['Repo']
    file_name = 'lens.json'
    execution_id = context.aws_request_id
    aws_account_id = context.invoked_function_arn.split(":")[4]
    aws_region = os.getenv('AWS_REGION')

    logger.info("Deploying Lens:")
    logger.info("Repo: {}".format(repo))
    logger.info("Branch: {}".format(branch))
    logger.info("CommitId: {}".format(commit_id))

    try: 
        response = codecommit.get_file(
            repositoryName=repo,
            commitSpecifier=commit_id,
            filePath=file_name
        )
        lens = json.loads(response['fileContent'].decode("utf-8"))
    except botocore.exceptions.ClientError as error:
        error_message = "{}: {}".format(error.response['Error']['Code'], error.response['Error']['Message'])
        put_job_failure(job_id, error_message, execution_id)
        raise
    except ValueError as error:
        error_message = "Error getting file {} from {}: Invalid JSON".format(file_name, repo)
        put_job_failure(job_id, error_message, execution_id)
        raise

    lens_name_normalized = lens['name'].lower().replace(' ', '-')
    lens_name = lens['name']
    lens_alias = "arn:aws:wellarchitected:{}:{}:lens/{}".format(aws_region, aws_account_id, lens_name_normalized)
    lens_version = lens.get('_version', '1.0')

    # list existing lenses
    lenses = wellarchitected.list_lenses(
        LensType='CUSTOM_SELF',
        LensStatus='ALL',
        LensName=lens_name
    )
    
    if len(lenses['LensSummaries']) > 0: # update existing lens
        args = {
            'LensAlias': lenses['LensSummaries'][0]['LensArn'],
            'JSONString': json.dumps(lens) 
        }
    else: # import new lens
        args = {
            'JSONString': json.dumps(lens) 
        }
    
    try:
        response = wellarchitected.import_lens(**args)
        lens_arn = response['LensArn']
        wellarchitected.tag_resource(
            WorkloadArn=lens_arn,
            Tags={
                'LensAlias': lens_alias,
                'Repository': repo,
                'Branch': branch,
                'CommitId': commit_id
            }
        )
    except botocore.exceptions.ClientError as error:
        error_message = "{}: {}".format(error.response['Error']['Code'], error.response['Error']['Message'])
        logger.error(error_message)
        put_job_failure(job_id, error_message, execution_id)
        raise

    # create new lens version
    try:
        wellarchitected.create_lens_version(
            LensAlias=lens_arn,
            LensVersion=lens_version,
            IsMajorVersion=True
        )
    except botocore.exceptions.ClientError as error:
        error_message = "{}: {}".format(error.response['Error']['Code'], error.response['Error']['Message'])
        logger.error(error_message)
        put_job_failure(job_id, error_message, execution_id)
        wellarchitected.delete_lens(
            LensAlias=lens_arn,
            LensStatus='DRAFT'
        )
        raise

    put_job_success(job_id)
