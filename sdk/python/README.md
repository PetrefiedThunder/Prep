# Prep Compliance API Python SDK

This package provides an async-friendly Python client for the Prep Compliance API generated from
`contracts/openapi/prep.yaml`. The client uses [`httpx`](https://www.python-httpx.org/) under the
hood and ships with convenience helpers for each documented endpoint.

## Installation

```bash
pip install .
```

## Usage

```python
import asyncio

from prep_sdk import AuthenticatedClient
from prep_sdk.api.city import list_city_fees

async def main() -> None:
    client = AuthenticatedClient(base_url="https://api.prep.house/v1", api_key="my-api-key")
    response = await list_city_fees.asyncio(
        "san-francisco-ca",
        client=client,
        business_type="restaurant",
    )
    if response:
        for fee in response.fees:
            print(fee.name, fee.amount)

asyncio.run(main())
```

Refer to the generated modules under `prep_sdk.api` and `prep_sdk.models` for the full surface area.
