import React from 'react';
import Image from 'next/image';

interface LogoProps {
  size?: 'small' | 'medium' | 'large' | 'xlarge';
  variant?: 'full' | 'text-only' | 'icon-only';
  className?: string;
  showVersion?: boolean;
  showSaaS?: boolean;
}

/**
 * DataAgent V4.1 Logo组件
 *
 * @param size - 尺寸: small(64x16), medium(128x32), large(256x64), xlarge(320x80)
 * @param variant - 变体: full(完整logo), text-only(仅文字), icon-only(仅图标)
 * @param className - 额外的CSS类名
 * @param showVersion - 是否显示版本号
 * @param showSaaS - 是否显示SaaS标签
 */
const Logo: React.FC<LogoProps> = ({
  size = 'medium',
  variant = 'full',
  className = '',
  showVersion = true,
  showSaaS = true
}) => {
  // 尺寸配置
  const sizeConfig = {
    small: { width: 64, height: 16 },
    medium: { width: 128, height: 32 },
    large: { width: 256, height: 64 },
    xlarge: { width: 320, height: 80 }
  };

  const { width, height } = sizeConfig[size];

  // 根据变体选择不同的logo文件
  const getLogoSrc = () => {
    if (variant === 'text-only') {
      return '/logo-text-only.svg'; // 可以创建文字版logo
    }
    if (variant === 'icon-only') {
      return '/logo-icon-only.svg'; // 可以创建图标版logo
    }
    return '/logo.svg';
  };

  const logoProps = {
    src: getLogoSrc(),
    alt: 'DataAgent V4.1 Logo',
    width,
    height,
    className: `transition-all duration-200 ${className}`
  };

  return (
    <div className={`logo-container logo-${size} logo-${variant} ${className}`}>
      <Image {...logoProps} alt="Data Agent Logo" />

      {/* 可选的版本和SaaS标识 */}
      {(showVersion || showSaaS) && size !== 'small' && (
        <div className="logo-badges flex items-center gap-1 ml-2">
          {showSaaS && (
            <span className="bg-green-100 text-green-800 text-xs px-1.5 py-0.5 rounded-full font-medium">
              SaaS
            </span>
          )}
          {showVersion && (
            <span className="bg-purple-100 text-purple-800 text-xs px-1.5 py-0.5 rounded-full font-medium">
              V4.1
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export default Logo;

// 使用示例
export const LogoExample = () => {
  return (
    <div className="space-y-4 p-6">
      <h2 className="text-xl font-bold mb-4">DataAgent Logo使用示例</h2>

      {/* 不同尺寸 */}
      <div className="space-y-2">
        <h3 className="text-lg font-semibold">不同尺寸</h3>
        <div className="flex items-center gap-4">
          <Logo size="small" />
          <Logo size="medium" />
          <Logo size="large" />
          <Logo size="xlarge" />
        </div>
      </div>

      {/* 不同变体 */}
      <div className="space-y-2">
        <h3 className="text-lg font-semibold">不同变体</h3>
        <div className="flex items-center gap-4">
          <Logo variant="full" showVersion={false} showSaaS={false} />
          <Logo variant="text-only" />
          <Logo variant="icon-only" />
        </div>
      </div>

      {/* 带标签的logo */}
      <div className="space-y-2">
        <h3 className="text-lg font-semibold">带标识的Logo</h3>
        <div className="flex items-center gap-4">
          <Logo showVersion={true} showSaaS={true} />
          <Logo showVersion={true} showSaaS={false} />
          <Logo showVersion={false} showSaaS={true} />
        </div>
      </div>
    </div>
  );
};