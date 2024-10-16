import logging
import traceback
from flask import jsonify


def server_success(msg="Request successful!", payload=None, uuid_request='', image=False):
    if payload is None:
        payload = {}
    return jsonify(dict(status='ok', msg=msg, payload=payload, uuid_request=uuid_request, image=image)), 200


def server_failed(msg="Request failed!"):
    return jsonify(dict(status='error', msg=msg)), 500


def get_args(req):
    logging.info('start /get_args')

    rv = {}
    logging.info('checking json')
    if req.is_json:
        logging.info('it\'s json')
        try:
            rv = req.get_json()
        except:
            logging.error(
                'got exception on get_json(). (This can happen if the headers say it\'s JSON but the request doesn\'t '
                'have a body)')
    else:
        logging.info('it\'s not json')

    if not rv:
        try:
            logging.info('checking req.values')
            if req.values:
                logging.info('has req.values')
                rv = req.values
            else:
                logging.info('has no req.values')
        except BaseException:
            logging.error('got exception on req.values')
            logging.error(traceback.format_exc())
    logging.info('end /get_args')
    return rv

# def get_body_json():
#     args = get_args()
#     body_json = args.get('body-json')
#     logging.info('body_json: {}'.format(body_json))
#     if not body_json:
#         raise Exception('missing body arguments')
#     return body_json
