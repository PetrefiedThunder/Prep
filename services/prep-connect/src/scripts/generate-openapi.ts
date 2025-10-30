import { writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { buildOpenApiSchema } from '../openapi/schema';

function main() {
  const spec = buildOpenApiSchema();
  const outputPath = resolve(__dirname, '../../dist/openapi.json');
  writeFileSync(outputPath, JSON.stringify(spec, null, 2));
  // eslint-disable-next-line no-console
  console.log(`OpenAPI schema written to ${outputPath}`);
}

main();
