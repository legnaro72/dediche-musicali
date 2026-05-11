// astro.config.mjs
// IMPORTANTE: Modifica USERNAME e NOME-REPOSITORY con i tuoi valori GitHub
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://legnaro72.github.io',
  base: '/dediche-musicali',
  integrations: [sitemap()],
  output: 'static',
});
