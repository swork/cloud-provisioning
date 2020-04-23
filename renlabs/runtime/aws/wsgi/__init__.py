"""\
Pass an AWS Lambda invocation triggered by HTTP to a WSGI app, handling
the differences between how various AWS Lambda invocation mechanisms present
requests and expect responses.

Each bare function below can serve as lambda_handler() for one (any) of the
Python runtimes available in Lambda, accepting HTTP request events from various
sources:

 - [ ] APIGateway, AWS_PROXY integration
       - [ ] v1 payload option: wsgi_lambda_handler_APIGatewayv1
       - [ ] v2 payload option: wsgi_lambda_handler_APIGatewayv2
   Or wsgi_lambda_handler_APIGateway to auto-detect between them at small runtime cost.
 - [ ] Lambda@Edge
 - [ ] Elastic Load Balancer

"""

# LEVEL set at Lambda affects logging outside of request context.
# LEVEL set at API Gateway (or L@E? ELB?) affects logging during request processing.
import logging, os
logging.basicConfig(datefmt='')
logger = logging.getLogger(__name__)
logger.setLevel(int(os.environ.get('LEVEL', logging.DEBUG)))

# Import more symbols than necessary (convenience package imports). Cost of
# doing so is tiny as they're already loaded.
from .lambda_edge import (
    wsgi_lambda_handler_LambdaAtEdge,
    wsgi_lambda_handler_LambdaAtEdge_viewer,
    wsgi_lambda_handler_LambdaAtEdge_origin )
from .apigateway import wsgi_lambda_handler_APIGateway
from .apigatewayv1 import wsgi_lambda_handler_APIGatewayv1
from .apigatewayv2 import wsgi_lambda_handler_APIGatewayv2

def wsgi_lambda_handler(app_object, event, context):
    r = event.get('Records')
    if r and 'cf' in r[0]:
        return wsgi_lambda_handler_LambdaAtEdge(app_object, event, context)
    elif event.get('elb'):
        raise RuntimeError("Elastic Load Balancer not yet supported for WSGI by this module")
    elif event.get('version'):
        return wsgi_lambda_handler_APIGateway(app_object, event, context)
    raise RuntimeError("Unrecognized event payload schema")

