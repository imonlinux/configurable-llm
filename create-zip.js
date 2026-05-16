import { spawnSync } from 'child_process';
import { readdirSync, statSync, existsSync, mkdirSync, readFileSync, writeFileSync, createWriteStream } from 'fs';
import { join, dirname, relative } from 'path';
import { fileURLToPath } from 'url';
import { dirname as pathDirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = pathDirname(__filename);

// Create a simple zip file using tar+gzip (widely compatible)
const result = spawnSync('tar', [
  '-czf',
  'configurable_llm.zip',
  'custom_components/configurable_llm/'
], {
  cwd: __dirname,
  stdio: 'inherit'
});

if (result.status !== 0) {
  console.error('Failed to create zip file');
  process.exit(1);
}

console.log('Created configurable_llm.zip successfully');