# ETL Crawler

The asynchronous crawler in `etl/crawler.py` downloads documents and uploads
them to S3 using the following command line pattern:

```bash
env CRAWLER_BUCKET=prep-etl-raw python -m etl.crawler <<'EOF'
ca,https://example.com/regulations.pdf
wa https://another.example.com/notice.html
EOF
```

## Input format

Each non-empty line read from standard input must include a jurisdiction and a
URL separated by a comma, tab, or whitespace. Lines beginning with `#` are
ignored.

## AWS configuration

Uploads rely on the default [boto3 credential resolution
chain](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html).
Set one of the following before running the crawler:

- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and (optionally)
  `AWS_SESSION_TOKEN`
- or configure an [AWS shared credentials
  profile](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
- or execute the crawler on infrastructure that provides an IAM role with
  `s3:PutObject` permissions on the `prep-etl-raw` bucket.

The crawler also honors these optional environment variables:

- `CRAWLER_BUCKET` – overrides the default destination bucket (`prep-etl-raw`).
- `CRAWLER_CONCURRENCY` – controls the maximum number of concurrent fetches.
- `CRAWLER_DATE` – sets the `{date}` prefix used when constructing S3 keys.

## Output structure

Objects are written to `s3://prep-etl-raw/{date}/{jurisdiction}/{filename}`.
The `{date}` component defaults to the current UTC date unless overridden via
`CRAWLER_DATE`. Each S3 object includes an `sha256` metadata entry containing
the SHA-256 hash of the uploaded payload.

## Error handling

The crawler retries HTTP 5xx responses with exponential backoff and emits
log entries at `WARNING` level. Failures after the configured number of
attempts cause the process to exit with a non-zero status.
