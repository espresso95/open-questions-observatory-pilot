import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';
const reports = defineCollection({
  loader: glob({ pattern: '*.md', base: './src/content/reports' }),
  schema: z.object({ title: z.string(), description: z.string() })
});
export const collections = { reports };
