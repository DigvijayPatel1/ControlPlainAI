import { cpSync, mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const root = path.dirname(fileURLToPath(import.meta.url))
const extensionRoot = path.resolve(root, '..')
const dist = path.join(extensionRoot, 'dist')

mkdirSync(dist, { recursive: true })
cpSync(path.join(extensionRoot, 'manifest.json'), path.join(dist, 'manifest.json'))

console.log('✓ copied manifest.json into dist/')