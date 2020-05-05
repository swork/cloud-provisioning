# see __init__.py for note about environ context
import logging, os, json
logging.basicConfig(datefmt='')
logger = logging.getLogger(__name__)
logger.setLevel(int(os.environ.get('LEVEL', logging.DEBUG)))

from .apigateway_common import (
    set_level_for_apigateway_event,
    restore_level,
    ResponseWrapperAPIGateway )
from werkzeug.test import Client, EnvironBuilder
from werkzeug.datastructures import Headers

def wsgi_lambda_handler_APIGatewayv2(app_object, event, context):
    saveLevel = set_level_for_apigateway_event(logger, event)
    logger.debug(f'event: {json.dumps(event)}')

    def werkzeug_headers_from_v2(h1):
        h = Headers()
        for k, v in h1.items():
            h.add(k.lower(), v)
        return h
    wzh = werkzeug_headers_from_v2(event.get('headers'))

    def _(event):
        epath = event['rawPath']
        rctx = event['requestContext']
        estage = rctx.get('stage')
        if estage and estage != '$default' and estage == epath[1:len(estage)+1]:
            maybe_slash_stage = '/' + estage
            adjusted_path = epath[len(estage)+1:]
        else:
            maybe_slash_stage = ''
            adjusted_path = epath
        return (f'http://{rctx["domainName"]}:443{maybe_slash_stage}',
                adjusted_path)
    base_url, adjusted_path  = _(event)
    logger.debug(f'event->environ - assigning base_url:{base_url}, adjusted_path:{adjusted_path}. Headers: {wzh!r}')

    b = EnvironBuilder(
        path=adjusted_path,
        base_url=base_url,
        headers=wzh.to_wsgi_list(),
        query_string=event['rawQueryString'],
        method=event['requestContext']['http']['method'])
    logger.debug(f'{__name__} environ: {b.get_environ()}')
    response = Client(app_object, ResponseWrapperAPIGateway).open(b).get_response()
    restore_level(logger, saveLevel)
    return response

