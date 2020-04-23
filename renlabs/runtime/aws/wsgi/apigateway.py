# see __init__.py for note about environ context
import logging, os
logging.basicConfig(datefmt='', level=int(os.environ.get('LEVEL', logging.DEBUG)))
logger = logging.getLogger(__name__)

from .apigatewayv1 import wsgi_lambda_handler_APIGatewayv1

def wsgi_lambda_handler_APIGateway(app_object, event, context):
    if event.get('version') == '2.0':
        return wsgi_lambda_handler_APIGatewayv2(app_object, event, context)
    elif event.get('version') == '1.0':
        return wsgi_lambda_handler_APIGatewayv1(app_object, event, context)
    elif 'rawPath' in event:
        return wsgi_lambda_handler_APIGatewayv2(app_object, event, context)
    else:
        return wsgi_lambda_handler_APIGatewayv1(app_object, event, context)
    raise RuntimeError("Unrecognized event payload schema")

