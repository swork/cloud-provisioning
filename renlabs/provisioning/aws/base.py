import boto3, logging

logger = logging.getLogger(__name__)

class AWSBase:
    """
    Class method get_class() returns a class which, when instantiated, knows
    details of AWS interactions already. Subclass THAT to make
    application-specific AWS manipulation objects that don't need per-instance
    or per-class configuration. (A similar thing could be done by passing
    around a configuration object, but this might hide the details better)
    """

    app = dict()
    _iamClient = None
    _iam_get_user = None
    _account = None
    _region = None
    _provisioning_tag = None
    _lambdaClient = None
    _apiClient = None
    _s3Client = None

    def __init__(self):
        if self.__class__ == AWSBase:
            logger.warn(f"""Don't instantiate {self.__class__!r} directly.
Run AWSBase.class_configure once, and build on subclass instances.""")

    @classmethod
    def class_configure(cls, region, provisioning_tag, app={}):
        """
        Do some basic AWS lookups once, so subclass instances have basic info
        available.
        """
        cls.app.update(app)

        cls._region = region
        cls._provisioning_tag = provisioning_tag

        # Lazy-instantiate clients where we can, but need this one now
        cls._iamClient = boto3.client('iam')
        cls._iam_get_user = cls._iamClient.get_user()['User']
        cls._account = cls._iam_get_user['Arn'].split(':')[4]

    @property
    def account(self):
        return self._account

    @property
    def region(self):
        return self._region

    @property
    def provisioning_tag(self):
        return self._provisioning_tag

    @property
    def iamClient(self):
        if not self._iamClient:
            logger.warning('Did you call AWSBase.class_configure()?')
            self._iamClient = boto3.client('iam')
        return self._iamClient

    @property
    def lambdaClient(self):
        if not self._lambdaClient:
            self._lambdaClient = boto3.client('lambda')
        return self._lambdaClient

    @property
    def apiClient(self):
        if not self._apiClient:
            self._apiClient = boto3.client('apigatewayv2')
        return self._apiClient

    @property
    def s3Client(self):
        if not self._s3Client:
            self._s3Client = boto3.client('s3')
        return self._s3Client
