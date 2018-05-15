import json
import logging
import requests


def init_logging():
    # lambci adds root logging handler, we have to remove it first
    root_logger = logging.getLogger()
    for h in root_logger.handlers:
        root_logger.removeHandler(h)
    logging.basicConfig(level=logging.INFO)


def make_request(url: str) -> dict:
    logging.info("Starting request")
    response = requests.get(url=url)
    logging.info(f"Request done, status code: {response.status_code}")
    return {
        "statusCode": response.status_code,
        "url": response.url
    }


def handler(event, context):
    init_logging()
    logging.info(f"Event: {event}")
    return make_request(
        url=event.get('url', 'http://example.com')
    )


def api_handler(event, context):
    init_logging()
    logging.info(f"Event: {event}")
    body = event.get('body', '')
    event = json.loads(body)
    url = event.get('url', 'http://example.com')
    response_data = make_request(url=url)
    return {
        'statusCode': response_data['statusCode'],
        'isBase64Encoded': False,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(response_data)
    }
