/** @type {import('next').NextConfig} */
const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true',
})

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

    // 忽略文件系统扫描错误的目录
    config.watchOptions = {
      ignored: [
        '**/__tests__/**',
        '**/node_modules/**',
        '**/.git/**',
        '**/.next/**',
      ],
      poll: 1000, // 每秒检查一次变化
      aggregateTimeout: 300, // 延迟重新构建时间
    }

    return config
  },
}

module.exports = withBundleAnalyzer(nextConfig)