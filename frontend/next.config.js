/** @type {import('next').NextConfig} */
const nextConfig = {
  // 暂时注释掉 standalone 模式以消除构建警告，在生产环境需要时可以启用
  // output: 'standalone',
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