import assert from 'node:assert/strict';
import { createMarkdownProcessor } from '@astrojs/markdown-remark';
import rehypeSanitize from 'rehype-sanitize';
const processor = await createMarkdownProcessor({remarkRehype:{allowDangerousHtml:false},rehypePlugins:[rehypeSanitize]});
const rendered = await processor.render('<script>throw new Error("unsafe")</script>\n\n[x](javascript:alert(1))\n\n[safe](https://psl.noaa.gov/)');
assert(!rendered.code.includes('<script'));
assert(!rendered.code.includes('javascript:'));
assert(rendered.code.includes('https://psl.noaa.gov/'));
console.log('PASS: executable HTML and unsafe link protocols removed; safe source links retained.');
