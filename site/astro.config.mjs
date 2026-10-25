import { defineConfig } from 'astro/config';
import { unified } from '@astrojs/markdown-remark';
import rehypeSanitize from 'rehype-sanitize';
export default defineConfig({
  output: 'static',
  base: process.env.SITE_BASE || '/',
  markdown: { processor: unified({ remarkRehype: { allowDangerousHtml: false }, rehypePlugins: [rehypeSanitize] }) },
  vite: { server: { host: '127.0.0.1' } }
});
