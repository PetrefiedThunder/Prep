import { strict as assert } from 'node:assert';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';
import { createRequire } from 'node:module';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '../../../..');
const primaryRequire = createRequire(path.join(repoRoot, 'package.json'));
let ts;
try {
  ts = primaryRequire('typescript');
} catch (error) {
  const fallbackRequire = createRequire(path.join(repoRoot, 'apps/web/package.json'));
  ts = fallbackRequire('typescript');
}

async function loadConnectorModule() {
  const filePath = path.resolve(__dirname, '../../../../sdk/connectors/base.ts');
  const source = await readFile(filePath, 'utf8');
  const transpiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2021,
      esModuleInterop: true,
    },
    fileName: filePath,
  });

  const exports = {};
  const module = { exports };
  const localRequire = createRequire(filePath);
  const context = {
    module,
    exports,
    require: localRequire,
    process,
    Buffer,
    console,
    setTimeout,
    setImmediate,
    clearTimeout,
    clearImmediate,
  };
  vm.createContext(context);
  const script = new vm.Script(transpiled.outputText, { filename: filePath });
  script.runInContext(context);
  return module.exports;
}

const modulePromise = loadConnectorModule();

test('Square connector normalizes payments into canonical response', async () => {
  const { SquareConnector } = await modulePromise;
  const connector = new SquareConnector();
  const response = await connector.fetchData({ limit: 1 });

  assert.equal(response.records.length, 1);
  const [record] = response.records;
  assert.equal(record.id, 'GQTFp1ZlXdpoW4o6eGiZ');
  assert.equal(record.attributes.status, 'COMPLETED');
  assert.ok(!('id' in record.attributes), 'Normalized attributes should not expose id');
  assert.equal(response.meta.source, 'square.payments');
  assert.equal(response.meta.sandbox, true);
});

test('DoorDash Drive connector normalizes delivery records', async () => {
  const { DoorDashDriveConnector } = await modulePromise;
  const connector = new DoorDashDriveConnector();
  const response = await connector.fetchData({ limit: 2 });

  assert.equal(response.records.length, 2);
  const [first, second] = response.records;
  assert.equal(first.id, 'dd-delivery-1001');
  assert.equal(second.attributes.status, 'picked_up');
});

test('MarketMan connector exposes pending webhook registration status', async () => {
  const { MarketManConnector } = await modulePromise;
  const connector = new MarketManConnector();
  const webhook = await connector.registerWebhook('https://example.com/webhooks/marketman');

  assert.equal(webhook.status, 'pending');
  assert.equal(webhook.id, 'sandbox-marketman-webhook');
});
