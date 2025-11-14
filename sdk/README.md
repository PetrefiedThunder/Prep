## Generate SDKs

### TypeScript
```bash
npm i -D openapi-typescript
npx openapi-typescript ../contracts/openapi/prep.yaml -o typescript/index.d.ts
```

### Python
```bash
pip install openapi-python-client
openapi-python-client generate --path ../contracts/openapi/prep.yaml --output python
```
