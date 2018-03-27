import requests


def handler(event, context):
    response = requests.get('http://example.com')
    return {
        "statusCode": response.status_code,
        "url": response.url
    }
