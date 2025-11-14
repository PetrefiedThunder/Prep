import nextConfig from 'eslint-config-next';

export default [
  ...nextConfig,
  {
    rules: {
      '@next/next/no-img-element': 'off'
    }
  }
];
