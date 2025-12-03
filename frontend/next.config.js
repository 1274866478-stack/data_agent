/** @type {import('next').NextConfig} */
const nextConfig = {
  // 启用 standalone 模式以支持 Docker 部署
  output: 'standalone',
  transpilePackages: [],
  experimental: {
    optimizePackageImports: ['lucide-react', '@radix-ui/react-slot', '@radix-ui/react-label']
  },
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': './src',
      '@/components': './src/components',
      '@/lib': './src/lib',
      '@/store': './src/store',
      '@/app': './src/app',
    }

    return config
  },
}

module.exports = nextConfig