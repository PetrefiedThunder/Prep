import path from 'path';
import { fileURLToPath } from 'url';

const locales = ['en', 'es'];
const dirname = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverActions: {
      bodySizeLimit: '2mb'
    }
  },
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'images.unsplash.com' },
      { protocol: 'https', hostname: 'plus.unsplash.com' }
    ]
  },
  // i18n config removed - not supported in App Router, use next-intl instead
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'Permissions-Policy',
            value: 'interest-cohort=()'
          }
        ]
      }
    ];
  },
  // Turbopack config to replace webpack
  turbopack: {
    resolveAlias: {
      '@': path.join(dirname)
    }
  }
};

export default nextConfig;
