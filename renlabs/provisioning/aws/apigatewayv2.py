from .base import AWSBase
from botocore.exceptions import ClientError
from .awslambda import LambdaFunction

class GatewayApi(AWSBase):
    def __init__(self):
        super().__init__()
        _function = LambdaFunction().find()
        self._function_arn = _function._function_arn
        self._api_id = None
        self._integration_id = None

    def find_all(self):
        """
        Weirdly multiple API Gateway items can share a name. Here's a list of objects like:
        {
            "id": "27yl8znwne",
            "name": "dlproto2",
            "description": "Bare REST api prototype",
            "createdDate": 1579906860,
            "apiKeySource": "HEADER",
            "endpointConfiguration": {
                "types": [
                    "REGIONAL"
                ]
            }
        }
        """
        # More weirdness: 'apigatewayv2' won't report entities created through
        # 'apigateway' and vice versa, beware.
        items = self.apiClient.get_apis()
        my_items = list(filter(lambda x: x['Name'] == self.app['name'], items['Items']))
        return my_items

    def find(self):
        my_items = self.find_all()
        self._api_id = my_items[0]['ApiId']
        self._endpoint = my_items[0]['ApiEndpoint']

        self._integration_id = None
        integrations_items = self.apiClient.get_integrations(ApiId=self._api_id)['Items']
        if len(integrations_items) and len(integrations_items) != 1:
            raise RuntimeError(f"More than one integration for apigatewayv2 {self._api_id}")
        if len(integrations_items):
            self._integration_id = integrations_items[0]['IntegrationId']

        return self

    def create(self):
        description = "Data logging REST API"

        for item in self.find_all():
            raise RuntimeError(f"GatewayApi item with name {self.app['name']} already exists")

        created_api = self.apiClient.create_api(
            Name=self.app['name'],
            ProtocolType="HTTP",
            Description=self.app['gateway_description'],
            Tags = {
                "provisioning": self.provisioning_tag
            })
        self._api_id = created_api['ApiId']
        self._endpoint = created_api['ApiEndpoint']

        # Wow that integrationUri parameter.
        # See http://docs.aws.amazon.com/apigateway/api-reference/resource/integration/#uri
        # And https://github.com/boto/boto3/issues/572
        integrationUri = (
            f'arn:aws:apigateway:{self.region}' +
            f':lambda:path/2015-03-31/functions/{self._function_arn}/invocations')
        integration_response = self.apiClient.create_integration(
            ApiId=self._api_id,
            IntegrationMethod='POST',
            IntegrationType="AWS_PROXY",
            IntegrationUri=integrationUri,
            PayloadFormatVersion="2.0"
        )
        self._integration_id = integration_response['IntegrationId']

        stage_response = self.apiClient.create_stage(
            ApiId=self._api_id,
            AutoDeploy=True,
            StageName=self.app['gateway_stage_name'],
            Tags={
                "provisioning": self.provisioning_tag
            }
        )
        # More stages can be added by hand, so this one can be treated as
        # pre-production; they'll need to be destroyed by hand too.

        return self

    def destroy(self):
        self.find()
        try:
            self.apiClient.delete_stage(ApiId=self._api_id, StageName=self.app['gateway_stage_name'])
        except ClientError:
            pass

        if self._integration_id:
            try:
                self.apiClient.delete_integration(ApiId=self._api_id, IntegrationId=self._integration_id)
            except ClientError:
                pass

        for item in self.find_all():
            self.apiClient.delete_api(ApiId=item['ApiId'])


class Route(AWSBase):
    """Set up a single endpoint ("route")"""
    def __init__(self, method=None, path=None):
        """ no leading slash on path; None, None for $default route """
        super().__init__()
        self._method = method
        self._path = path
        self._routeKey = f"{method} /{path}" if method and path else '$default'
        self._gatewayapi = GatewayApi().find()
        self._api_id = self._gatewayapi._api_id
        self._integration_id = self._gatewayapi._integration_id
        self._route_id = None

    def find(self):
        routes_response = self.apiClient.get_routes(ApiId=self._api_id)
        self._route_id = None
        for item in routes_response['Items']:
            if item['RouteKey'] == self._routeKey:
                self._route_id = item['RouteId']
                break
        if self._route_id is None:
            raise RuntimeError(f"No endpoint {self._routeKey!r}")
        return self

    def create(self):
        route_response = self.apiClient.create_route(
            ApiId=self._api_id,
            AuthorizationType='NONE',
            RouteKey=self._routeKey,
            Target=f"integrations/{self._integration_id}"
        )
        self._route_id = route_response['RouteId']
        LambdaFunction().find().permit(self._api_id, 'apigateway.amazonaws.com')
        print(f"{self._method or 'Any'}: {self._gatewayapi._endpoint}/{self._gatewayapi.app['gateway_stage_name']}/{self._path or ''}")
        return self

    def destroy(self):
        self.find()

        if self._route_id:
            try:
                self.apiClient.delete_route(ApiId=self._api_id, RouteId=self._route_id)
            except ClientError:
                pass

class DefaultRoute(Route):
    def __init__(self):
        super().__init__(None, None)

