import fs from 'node:fs/promises';
import path from 'node:path';
const base = process.env.SITE_BASE || '/';
if (!/^\/(?:[a-zA-Z0-9_-]+\/)*$/.test(base)) throw new Error('Invalid static site base');
async function walk(dir) {
  for (const item of await fs.readdir(dir, { withFileTypes: true })) {
    const p = path.join(dir, item.name);
    if (item.isDirectory()) await walk(p);
    else if (p.endsWith('.html') && base !== '/') {
      let text = await fs.readFile(p, 'utf8');
      text = text.replace(/\b(href|src)="\/(?!\/)([^"]*)"/g, (all, attr, rest) =>
        rest.startsWith(base.slice(1)) ? all : `${attr}="${base}${rest}"`);
      await fs.writeFile(p, text);
    }
  }
}
await walk('dist');
