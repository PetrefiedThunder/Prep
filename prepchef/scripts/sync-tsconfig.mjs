#!/usr/bin/env node
import { promises as fs } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..');

const TEST_EXCLUDES = [
  'src/**/*.test.ts',
  'src/**/*.test.tsx',
  'src/**/*.spec.ts',
  'src/**/*.spec.tsx',
  'src/tests/**'
];

const workspaces = [
  { name: 'packages', options: { rootDir: 'src', outDir: 'dist' } },
  { name: 'services', options: { rootDir: 'src', outDir: 'dist' } }
];

async function pathExists(targetPath) {
  try {
    await fs.access(targetPath);
    return true;
  } catch (error) {
    if (error.code === 'ENOENT') return false;
    throw error;
  }
}

async function ensureTsconfig(dir, compilerOptions) {
  const srcDir = path.join(dir, compilerOptions.rootDir);
  if (!(await pathExists(srcDir))) {
    return false;
  }

  const configPath = path.join(dir, 'tsconfig.json');
  const config = {
    extends: '@prep/tsconfig/tsconfig.base.json',
    compilerOptions,
    include: [compilerOptions.rootDir],
    exclude: TEST_EXCLUDES
  };

  const desired = `${JSON.stringify(config, null, 2)}\n`;

  try {
    const current = await fs.readFile(configPath, 'utf8');
    if (current === desired) {
      return false;
    }
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }

  await fs.writeFile(configPath, desired, 'utf8');
  return true;
}

async function syncWorkspace(workspace) {
  const baseDir = path.join(repoRoot, workspace.name);
  if (!(await pathExists(baseDir))) {
    return [];
  }

  const entries = await fs.readdir(baseDir, { withFileTypes: true });
  const updated = [];

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const dir = path.join(baseDir, entry.name);
    if (await ensureTsconfig(dir, { ...workspace.options })) {
      updated.push(path.relative(repoRoot, path.join(dir, 'tsconfig.json')));
    }
  }

  return updated;
}

async function main() {
  const updates = [];
  for (const workspace of workspaces) {
    const changed = await syncWorkspace(workspace);
    updates.push(...changed);
  }

  if (updates.length) {
    console.log(`Synchronized TypeScript configs for ${updates.length} workspace${updates.length === 1 ? '' : 's'}:`);
    for (const file of updates) {
      console.log(` - ${file}`);
    }
  } else {
    console.log('TypeScript workspace configuration already up to date.');
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
