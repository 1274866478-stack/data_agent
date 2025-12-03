import React from 'react';
import Logo, { LogoExample } from '@/components/Logo';

/**
 * Logo演示页面
 * 展示DataAgent V4.1 Logo的各种使用方式
 */
const LogoDemoPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部导航 */}
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Logo size="medium" />
            <div className="text-sm text-gray-500">
              DataAgent V4.1 Logo演示页面
            </div>
          </div>
        </div>
      </nav>

      {/* 主要内容 */}
      <main className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        {/* 页面标题 */}
        <div className="text-center mb-8">
          <Logo size="xlarge" className="mx-auto mb-4" />
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            DataAgent V4.1 Logo设计
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            专为多租户SaaS数据智能分析平台设计的品牌标识，
            体现数据流动、AI智能和企业级安全性。
          </p>
        </div>

        {/* Logo展示示例 */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <LogoExample />
        </div>

        {/* 设计说明 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* 设计特点 */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-bold mb-4 text-blue-600">设计特点</h2>
            <ul className="space-y-2 text-gray-700">
              <li className="flex items-start">
                <span className="text-blue-500 mr-2">•</span>
                <span><strong>3D字母D组合</strong> - 外层代表数据库，内层代表数据流</span>
              </li>
              <li className="flex items-start">
                <span className="text-green-500 mr-2">•</span>
                <span><strong>渐变色彩系统</strong> - 蓝色主调，青色辅助，紫色点缀</span>
              </li>
              <li className="flex items-start">
                <span className="text-purple-500 mr-2">•</span>
                <span><strong>AI核心元素</strong> - 中心圆点和连接线代表智能分析</span>
              </li>
              <li className="flex items-start">
                <span className="text-gray-500 mr-2">•</span>
                <span><strong>数据节点网络</strong> - 虚线和小圆点体现多租户连接</span>
              </li>
              <li className="flex items-start">
                <span className="text-orange-500 mr-2">•</span>
                <span><strong>SaaS版本标识</strong> - 清晰的V4.1和SaaS标签</span>
              </li>
            </ul>
          </div>

          {/* 色彩规范 */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-bold mb-4 text-purple-600">色彩规范</h2>
            <div className="space-y-3">
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 rounded bg-gradient-to-r from-blue-400 to-blue-600"></div>
                <div>
                  <div className="font-medium">主色调</div>
                  <div className="text-sm text-gray-500">#0EA5E9 → #3B82F6 → #6366F1</div>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 rounded bg-gradient-to-r from-green-400 to-green-600"></div>
                <div>
                  <div className="font-medium">辅助色</div>
                  <div className="text-sm text-gray-500">#10B981 → #059669</div>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 rounded bg-gradient-to-r from-purple-400 to-purple-600"></div>
                <div>
                  <div className="font-medium">AI元素色</div>
                  <div className="text-sm text-gray-500">#8B5CF6 → #6D28D9</div>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 rounded bg-gray-900"></div>
                <div>
                  <div className="font-medium">文字色</div>
                  <div className="text-sm text-gray-500">#1F2937</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 使用指南 */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-xl font-bold mb-4 text-green-600">使用指南</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="border border-green-200 rounded p-4">
              <h3 className="font-medium text-green-800 mb-2">✅ 推荐使用</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• 官网和产品页面</li>
                <li>• 文档和演示材料</li>
                <li>• 社交媒体头像</li>
                <li>• 营销宣传材料</li>
              </ul>
            </div>
            <div className="border border-blue-200 rounded p-4">
              <h3 className="font-medium text-blue-800 mb-2">💡 使用技巧</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• SVG格式保持清晰度</li>
                <li>• 根据场景选择合适尺寸</li>
                <li>• 深色背景考虑使用白色版</li>
                <li>• 保持安全边距</li>
              </ul>
            </div>
            <div className="border border-red-200 rounded p-4">
              <h3 className="font-medium text-red-800 mb-2">❌ 使用禁忌</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• 修改Logo颜色或形状</li>
                <li>• 添加第三方元素</li>
                <li>• 扭曲或变形使用</li>
                <li>• 与低质量内容关联</li>
              </ul>
            </div>
          </div>
        </div>

        {/* 技术信息 */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-bold mb-4 text-gray-600">技术信息</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <h3 className="font-medium mb-2">文件信息</h3>
              <table className="w-full text-gray-600">
                <tr>
                  <td className="py-1">主文件:</td>
                  <td className="py-1"><code>docs/design/logo/DataAgent_V4_1_Logo_Enhanced.svg</code></td>
                </tr>
                <tr>
                  <td className="py-1">前端文件:</td>
                  <td className="py-1"><code>frontend/public/logo.svg</code></td>
                </tr>
                <tr>
                  <td className="py-1">组件:</td>
                  <td className="py-1"><code>frontend/src/components/Logo.tsx</code></td>
                </tr>
                <tr>
                  <td className="py-1">格式:</td>
                  <td className="py-1">SVG矢量图</td>
                </tr>
                <tr>
                  <td className="py-1">标准尺寸:</td>
                  <td className="py-1">320×80px</td>
                </tr>
              </table>
            </div>
            <div>
              <h3 className="font-medium mb-2">开发参考</h3>
              <div className="bg-gray-50 rounded p-3 font-mono text-xs">
                <pre>{`// React组件使用
import Logo from '@/components/Logo';

<Logo size="medium" showVersion={true} />

// CSS背景使用
.logo {
  background-image: url('/logo.svg');
  background-size: contain;
}`}</pre>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* 页脚 */}
      <footer className="bg-white border-t mt-12">
        <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8">
          <div className="text-center text-sm text-gray-500">
            <Logo size="small" className="inline-block mr-2" />
            © 2025 DataAgent V4.1 - 多租户SaaS数据智能分析平台
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LogoDemoPage;