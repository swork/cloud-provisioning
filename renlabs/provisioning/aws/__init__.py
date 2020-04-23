import boto3, re

def get_tagged_role_names(provisioning_tag):
    c = boto3.client('iam')
    roles_response = c.list_roles()
    roles_names = map(lambda x: x['RoleName'], roles_response['Roles'])
    my_role_names = []
    for role_name in roles_names:
        role_tags_response = c.list_role_tags(RoleName=role_name)
        for tag in role_tags_response['Tags']:
            if tag['Key'] == 'provisioning' and tag['Value'] == provisioning_tag:
                my_role_names.append(role_name)
    return my_role_names

def nuke_roles(my_role_names):
    wipeouts = []
    for role_name in my_role_names:
        c = boto3.client('iam')
        policies_response = c.list_attached_role_policies(RoleName=role_name)
        for policy_arn in map(lambda x: x['PolicyArn'],
                              policies_response['AttachedPolicies']):
            c.detach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
        c.delete_role(RoleName=role_name)
        wipeouts.append("iam -> {}".format(role_name))
    return wipeouts

def get_gettable_tagged_things_arns(region, provisioning_tag):
    c = boto3.client('resourcegroupstaggingapi', region_name=region)
    f = {
        'Key': 'provisioning',
        'Values': [
            provisioning_tag
        ]
    }
    resources_response = c.get_resources(TagFilters=(f,))
    my_resources_arns = list(map(lambda x: x['ResourceARN'],
                                 resources_response['ResourceTagMappingList']))
    return my_resources_arns

def nuke_arns(region, my_resources_arns):
    wipeouts = []
    for arn in my_resources_arns:
        is_apigateway = re.match(rf'arn:aws:apigateway:{region}::/restapis/(?P<id>.*)$', arn)
        is_lambda     = re.match(rf'arn:aws:lambda:{region}:\d*:function:(?P<name>.*)$', arn)
        if is_apigateway:
            boto3.client('apigateway').delete_rest_api(is_apigateway.group('id'))
            wipeouts.append("apigateway -> {}".format(is_apigateway.group('id')))
        elif is_lambda:
            boto3.client('lambda').delete_function(FunctionName=is_lambda.group('name'))
            wipeouts.append("lambda -> {}".format(is_lambda.group('name')))
    return wipeouts


# convenience imports
from .base import AWSBase
from .apigatewayv2 import GatewayApi, Route, DefaultRoute
from .awslambda import LambdaFunction, LambdaExecutionRole

