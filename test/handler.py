import requests


def handler(event, context):
    response = requests.get('http://example.com')
    return {
        "statusCode": 200,
        "url": response.url
    }
