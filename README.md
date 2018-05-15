# python-lambda-local-server
![build](https://img.shields.io/docker/build/valian/python-lambda-local-server.svg)


A Docker image to help with development of a local AWS lambda Python functions.
Based on the [lambci/lambda](https://hub.docker.com/r/lambci/lambda/) image.
Created, because I haven't found an easy way to run lambda function locally.

Features:
* Automatically installs packages from requirements.txt during startup
* Mirrored AWS Lambda environment thanks to lambci images
* Code is reloaded for each submitted event
* Available simple Web UI for better workflow

# Usage

Go to directory with your lambda Python code. Next, run this command:

```language:bash
docker run -it \
  -p 8080:8080 \
  -v lambda-packages-cache:/packages/ \
  -v $PWD:/var/task/ \
  valian/python-lambda-local-server
```

It should automatically install packages from your requirements.txt and start web sever written in aiohttp.
To see web UI, head to http://localhost:8080. You should see a simple web UI for testing your lambda function.

![Event UI](https://raw.githubusercontent.com/valian/python-lambda-local-server/master/pictures/event_ui.png)

Assuming that you have your lambda entrypoint in `lambda.py` and handler is named `handler`, you should
type it into desired inputs. Next, add JSON body that should be passed to the function as an event, and press 'Submit event'.
Result and logs should be visible on the right panel after a moment.


# Example

First, clone this repository:

```bash
git clone https://github.com/Valian/python-lambda-local-server
cd python-lambda-local-server
```

Next, start server with a proper volume mounted:
``` bash
docker run -it \
  -p 8080:8080 \
  -v $PWD/example:/var/task/ \
  valian/python-lambda-local-server
```

## Web UI usage

Go to http://localhost:8080. You should see something like this:

![Event UI](https://raw.githubusercontent.com/valian/python-lambda-local-server/master/pictures/event_ui.png)

Specify file, handler and event and click `Submit event`.
It invokes handler and prints execution logs and return value.


Api gateway tab automatically formats event to an AWS API Gateway format:
![API UI](https://raw.githubusercontent.com/valian/python-lambda-local-server/master/pictures/api_ui.png)

## Console example

You can of course use `curl` to submit events. Start sever and type:

```bash
curl -XPOST localhost:8080 -d '{"event": {"url": "https://example.com"}, "file": "handler.handler"}'

{
  "stdout": {
    "statusCode": 200,
    "url": "https://example.com/"
  },
  "stderr": "START RequestId: b1891caf-c22b-4ce6-8639-e74862adae30 Version: $LATEST\nINFO:root:Starting request\nINFO:root:Request done, status code: 200\nEND RequestId: b1891caf-c22b-4ce6-8639-e74862adae30\nREPORT RequestId: b1891caf-c22b-4ce6-8639-e74862adae30 Duration: 803 ms Billed Duration: 900 ms Memory Size: 1536 MB Max Memory Used: 23 MB\n"
}
```

# TODO
* [ ] Add support for `Serverless.yml` file
* [ ] Cleanup code, better error codes
* [ ] Support for chaining lambda calls either through AWS SDK or API endpoint

# License

MIT
