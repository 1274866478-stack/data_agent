"""
# [SCHEMAS_WECHAT_WORK] 企业微信数据模型

## [HEADER]
**文件名**: wechat_work.py
**职责**: 定义企业微信相关的 Pydantic 模型
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2025-03-22): 初始版本

## [INPUT]
- 用户请求和企业微信回调数据

## [OUTPUT]
- Pydantic 模型实例

## [LINK]
**上游依赖**:
- [../../services/wechat_work.py](../../services/wechat_work.py) - 企业微信服务使用这些模型

**下游依赖**:
- [../api/v1/endpoints/wechat_work.py](../api/v1/endpoints/wechat_work.py) - API端点使用这些模型

## [POS]
**路径**: backend/src/app/schemas/wechat_work.py
**模块层级**: Level 2 (schemas层)
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


class WechatWorkConfig(BaseModel):
    """企业微信配置"""
    corp_id: str = Field(..., description="企业ID")
    corp_secret: str = Field(..., description="应用Secret")
    agent_id: int = Field(..., description="应用ID")
    token: str = Field(..., description="回调验证Token")
    encoding_aes_key: str = Field(..., description="消息加密密钥")


class WechatWorkMessage(BaseModel):
    """企业微信消息"""
    to_user_name: str = Field(..., alias="ToUserName", description="接收方企业号")
    from_user_name: str = Field(..., alias="FromUserName", description="发送方企业号")
    create_time: str = Field(..., alias="CreateTime", description="消息创建时间")
    msg_type: str = Field(..., alias="MsgType", description="消息类型")
    content: Optional[str] = Field(None, alias="Content", description="消息内容")
    msg_id: Optional[str] = Field(None, alias="MsgId", description="消息ID")
    agent_id: Optional[str] = Field(None, alias="AgentID", description="应用ID")

    class Config:
        populate_by_name = True  # 允许使用别名


class WechatWorkCallbackRequest(BaseModel):
    """企业微信回调请求"""
    msg_signature: str = Field(..., description="消息签名")
    timestamp: str = Field(..., description="时间戳")
    nonce: str = Field(..., description="随机数")
    echostr: Optional[str] = Field(None, description="验证时的随机字符串")


class WechatWorkSendMessage(BaseModel):
    """发送企业微信消息请求"""
    user_id: str = Field(..., description="用户ID")
    message: str = Field(..., description="消息内容")
    msg_type: str = Field(default="text", description="消息类型: text, markdown, textcard")
    title: Optional[str] = Field(None, description="标题（textcard类型使用）")
    description: Optional[str] = Field(None, description="描述（textcard类型使用）")
    url: Optional[str] = Field(None, description="跳转链接（textcard类型使用）")
    btn_txt: Optional[str] = Field(default="详情", description="按钮文字（textcard类型使用）")


class WechatWorkSendMessageResponse(BaseModel):
    """发送消息响应"""
    success: bool = Field(..., description="是否成功")
    message: Optional[str] = Field(None, description="响应消息")
    error: Optional[str] = Field(None, description="错误信息")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")


class WechatWorkUserInfo(BaseModel):
    """企业微信用户信息"""
    user_id: str = Field(..., description="用户ID")
    name: str = Field(..., description="用户姓名")
    department: List[int] = Field(default_factory=list, description="所属部门列表")
    mobile: Optional[str] = Field(None, description="手机号码")
    email: Optional[str] = Field(None, description="邮箱")
    status: int = Field(default=1, description="激活状态: 1=已激活, 0=已禁用")
    enable: int = Field(default=1, description="启用状态: 1=启用, 0=禁用")
    avatar: Optional[str] = Field(None, description="头像url")


class WechatWorkDepartment(BaseModel):
    """企业微信部门信息"""
    id: int = Field(..., description="部门ID")
    name: str = Field(..., description="部门名称")
    parent_id: int = Field(..., description="父部门ID")
    order: int = Field(default=0, description="在父部门中的次序值")


class WechatWorkCheckResponse(BaseModel):
    """企业微信连接检查响应"""
    enabled: bool = Field(..., description="是否已启用")
    connected: bool = Field(..., description="是否连接成功")
    message: str = Field(..., description="状态消息")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class WechatWorkMessageHistory(BaseModel):
    """企业微信消息历史记录"""
    id: str = Field(..., description="记录ID")
    user_id: str = Field(..., description="用户ID")
    user_name: Optional[str] = Field(None, description="用户姓名")
    message: str = Field(..., description="消息内容")
    msg_type: str = Field(default="text", description="消息类型")
    direction: str = Field(..., description="消息方向: inbound=收到, outbound=发送")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    processed: bool = Field(default=False, description="是否已处理")


class WechatWorkConfigUpdate(BaseModel):
    """企业微信配置更新"""
    enabled: Optional[bool] = Field(None, description="是否启用")
    corp_id: Optional[str] = Field(None, description="企业ID")
    corp_secret: Optional[str] = Field(None, description="应用Secret")
    agent_id: Optional[int] = Field(None, description="应用ID")
    token: Optional[str] = Field(None, description="回调验证Token")
    encoding_aes_key: Optional[str] = Field(None, description="消息加密密钥")


class WechatWorkAccessToken(BaseModel):
    """企业微信Access Token"""
    access_token: str = Field(..., description="访问令牌")
    expires_in: int = Field(..., description="过期时间(秒)")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
