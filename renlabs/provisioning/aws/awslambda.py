import zipfile, io, traceback, uuid, json, os
from botocore.exceptions import ClientError
from . import AWSBase, nuke_roles

class LambdaExecutionRole(AWSBase):
    def __init__(self):
        super().__init__()
        self._role_arn = None
        self._name = f"lambdaExecutionRole_{self.app['name']}"

    @property
    def name(self):
        return self._name

    def destroy(self):
        try:
            nuke_roles([self._name])
        except ClientError:
            pass

    def find(self):
        r = self.iamClient.get_role(RoleName=self._name)
        self._role_arn = r['Role']['Arn']
        return self

    def create(self):
        role_names = map(lambda x: x['RoleName'], self.iamClient.list_roles()['Roles'])
        if self._role_arn:
            raise RuntimeError("Role {} already has ARN {}".format(self._name, self._role_arn))
        if self._name in role_names:
            raise RuntimeError("Role {} already exists".format(self._name))

        arpd = json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                },
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "apigateway.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        })

        created_role = self.iamClient.create_role(
            Path="/",
            RoleName=self._name,
            AssumeRolePolicyDocument = arpd,
            Description="swork - Lambda and API Gateway permissions role",
            MaxSessionDuration=3600,
            Tags = [
                {
                    "Key": "provisioning",
                    "Value": self.provisioning_tag
                }
            ])

        for managed_policy_name in [
                'AmazonAPIGatewayInvokeFullAccess',
                'AmazonSNSFullAccess',
                'AWSLambdaFullAccess',
                'service-role/AWSLambdaBasicExecutionRole',
                'service-role/AWSLambdaSQSQueueExecutionRole',
                'service-role/AWSLambdaVPCAccessExecutionRole',
                'service-role/AmazonAPIGatewayPushToCloudWatchLogs']:
            self.iamClient.attach_role_policy(
                RoleName=self._name,
                PolicyArn="arn:aws:iam::aws:policy/{}".format(managed_policy_name))
        self._role_arn = created_role['Role']['Arn']
        return self


class LambdaFunction(AWSBase):
    def __init__(self):
        """code is local filename for lambda function file or zip archive"""
        super().__init__()
        self._function_arn = None
        self._function_name = f"lambda_{self.app['name']}"

    def _zipfile_bytes(self, filename):
        pkgType = filename.rsplit('.',1)[-1]
        if pkgType == 'zip':
            return open(filename, 'rb').read()  # yikes, RAM hog

        dirname, basename = os.path.split(filename)
        zf = io.BytesIO()
        z = zipfile.ZipFile(zf, 'x', compression=zipfile.ZIP_DEFLATED)
        z.write(os.path.join(dirname, basename), arcname=basename)
        z.close()
        return zf.getvalue()

    def find(self):
        fn = self.lambdaClient.get_function(FunctionName=self._function_name)
        self._function_arn = fn['Configuration']['FunctionArn']
        return self

    def create(self, role_arn, code_filename, timeout=3, memory_size=128):
        handler = "lambda_function.lambda_handler"
        created_function = self.lambdaClient.create_function(
            FunctionName=self._function_name,
            Runtime=self.app.get('lambda_runtime', 'python3.8'),
            Role=role_arn,
            Handler=handler,
            Description=self.app.get('lambda_description', ''),
            Timeout=timeout,
            MemorySize=memory_size,
            Publish=True,
            Code = {
                "ZipFile": self._zipfile_bytes(code_filename)
            },
            Tags = {
                "provisioning": self.app['provisioning_tag']
            })

        self._function_arn = created_function['FunctionArn']
        return self

    def update_handler(self, code_filename):
        self.lambdaClient.update_function_code(
            FunctionName=self._function_name,
            ZipFile=self._zipfile_bytes(code_filename),
            Publish=True
        )

    def permit(self, api_id, principal, method='$default', path_constraint=None):
        arn = f"arn:aws:execute-api:{self.region}:{self.account}:{api_id}/*/{method}"
        if path_constraint:
            arn += path_constraint
        self.lambdaClient.add_permission(
            Action='lambda:InvokeFunction',
            FunctionName=self._function_name,
            Principal=principal,
            StatementId=str(uuid.uuid4()),
            SourceArn=arn)

    def destroy(self):
        try:
            self.lambdaClient.get_function(FunctionName=self._function_name)
            try:
                self.lambdaClient.delete_function(FunctionName=self._function_name)
            except ClientError as e:
                traceback.print_exc()
                raise RuntimeError("Failed to delete Lambda function")
        except:
            pass
