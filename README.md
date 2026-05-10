#重新编译支持ARM64，感谢不懂和L原作者。 douniwan819/pansou-pancheck:latest

# PansouAndPanCheck

一个整合了 [pansou](https://github.com/fish2018/pansou) 搜索服务和 [PanCheck](https://github.com/Lampon/PanCheck) 链接有效性校验的代理服务。

## 功能特性

- 自动过滤无效的网盘链接，只返回有效链接
- 支持多种网盘平台（夸克、UC、百度、天翼、123云盘、115网盘、迅雷、阿里云等）
- 提供与原版 pansou 完全兼容的 API 接口
- 支持 pansou 认证接口（登录、验证、登出）
- 支持 pansou 链接有效性检测接口
- 支持 POST 和 GET 请求方式
- 详细的过滤统计日志

## 部署方式

### Docker 部署（推荐）

```bash
docker run -d -p 1566:1566 \
  --name pansou-and-pancheck \
  -e SEARCH_API_URL=http://192.168.50.50:1514 \
  -e CHECK_API_URL=http://192.168.50.50:7024/api/v1/links/check \
  silent7897/pansou-and-pancheck:latest
```

### 环境变量说明

- `SEARCH_API_URL`：pansou 服务地址（默认值：http://127.0.0.1:8888）
- `CHECK_API_URL`：PanCheck 服务校验接口地址（默认值：http://127.0.0.1/api/v1/links/check）
- `AUTH_ENABLED`：是否启用认证（默认值：false）
- `AUTH_USERS`：认证用户，格式为 `user1:pass1,user2:pass2`
- `AUTH_TOKEN_EXPIRY`：JWT 有效期，单位小时（默认值：24）
- `AUTH_JWT_SECRET`：JWT 签名密钥，生产环境建议显式配置固定强随机字符串
- `PANSOU_AUTH_ENABLED`：是否启用上游 pansou 认证（默认值：false）
- `PANSOU_AUTH_USERNAME`：上游 pansou 登录用户名
- `PANSOU_AUTH_PASSWORD`：上游 pansou 登录密码
- `PANSOU_AUTH_TOKEN`：可选，上游 pansou 固定 token；配置后优先使用，不再自动登录

启用认证时必须配置 `AUTH_USERS` 和固定的 `AUTH_JWT_SECRET`。本地运行会自动加载项目根目录下的 `.env` 文件。

`AUTH_*` 用于保护本代理服务，`PANSOU_AUTH_*` 用于本代理访问上游 pansou。上游 pansou 开启认证时，推荐配置 `PANSOU_AUTH_ENABLED=true`、`PANSOU_AUTH_USERNAME`、`PANSOU_AUTH_PASSWORD`，代理会自动登录并缓存 token；上游返回 401 时会自动刷新一次。

### 本地部署

```bash
git clone https://github.com/your-repo/pansou-and-pancheck.git
cd pansou-and-pancheck
pip install -r requirements.txt
SEARCH_API_URL=http://your-pansou-url CHECK_API_URL=http://your-check-url python main.py
```

生产环境建议使用 gunicorn：

```bash
gunicorn -k gevent -w 2 -b 0.0.0.0:1566 main:app
```

## API 接口

- `POST /api/auth/login`：认证登录，返回 JWT
- `GET /api/auth/verify`：验证 JWT 是否有效
- `POST /api/auth/logout`：登出（客户端丢弃 JWT）
- `POST /api/search`：搜索网盘资源
- `GET /api/search`：搜索网盘资源，完整透传 pansou 查询参数
- `POST /api/check/links`：检测链接有效性
- `GET /api/health`：健康检查，返回 `auth_enabled`

启用认证后，除 `/api/auth/login`、`/api/auth/logout`、`/api/health` 外，其他接口都需要携带 `Authorization: Bearer <token>`。

## 项目链接

- [pansou](https://github.com/fish2018/pansou)
- [pansou-web](https://github.com/fish2018/pansou-web)
- [PanCheck](https://github.com/Lampon/PanCheck)

- ## Star History

[<image-card alt="Star History Chart" src="https://api.star-history.com/svg?repos=Silent1566/PansouAndPanCheck&type=Date" ></image-card>](https://star-history.com/#Silent1566/PansouAndPanCheck&Date)

<!-- 或者更推荐带暗色适配的写法 -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=Silent1566/PansouAndPanCheck&type=Date&theme=dark" />
  <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=Silent1566/PansouAndPanCheck&type=Date" />
  <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=Silent1566/PansouAndPanCheck&type=Date" />
</picture>

