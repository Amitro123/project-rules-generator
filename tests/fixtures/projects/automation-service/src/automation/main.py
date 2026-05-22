"""Automation service entry point. Uses Flask + boto3 + Anthropic.

The AWS usage here (boto3) is the evidence that tech_stack should
include 'aws' — Bug7 reported AWS missing despite this kind of code.
"""

import boto3
from anthropic import Anthropic
from flask import Flask, request

app = Flask(__name__)
_s3 = boto3.client("s3")
_claude = Anthropic()


@app.post("/process")
def process():
    payload = request.get_json()
    _s3.put_object(Bucket="tickets", Key=payload["id"], Body=payload["body"])
    resp = _claude.messages.create(
        model="claude-opus-4-7",
        max_tokens=200,
        messages=[{"role": "user", "content": payload["body"]}],
    )
    return {"reply": resp.content[0].text}
