const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const root = path.resolve(__dirname, '..');
const input = path.join(root, 'contracts', 'openapi.yaml');
const outputDir = path.join(root, 'packages', 'generated');
const outputFile = path.join(outputDir, 'index.ts');

fs.mkdirSync(outputDir, { recursive: true });

try {
  execSync(`npx openapi-typescript ${input} --output ${outputFile}`, { stdio: 'inherit' });
  console.log('OpenAPI types generated at', outputFile);
} catch (err) {
  console.error('Failed to generate OpenAPI types:', err.message);
  process.exit(1);
}
