# 前端（Next.js App Router）

IdeaSense AI 前端应用。

## 快速启动
1) 安装依赖：
```bash
cd frontend
npm install
```
2) 配置 API 地址：
```bash
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1" > .env.local
```
可参考 `.env.local.example` 了解更多配置项。
3) 启动开发服务器：
```bash
npm run dev
```
浏览器打开 [http://localhost:3000](http://localhost:3000)。

## Admin Shell
- 管理端入口为 `/admin`，依赖 `/api/v1/session`。
- 需要后端先启动（见 `backend/README.md` / `backend/README.zh.md`）。
- Admin 概览仪表盘通过 `/api/v1/admin-api/overview` 获取实时数据（含 activity feed）。

## API Base URL

前端使用 `NEXT_PUBLIC_API_BASE_URL` 作为 API 路由的唯一来源：

- 当 `NEXT_PUBLIC_API_BASE_URL` 非空时，请求使用绝对地址，如 `${BASE}/api/v1/...`。
- 当 `NEXT_PUBLIC_API_BASE_URL` 为空或未设置时，请求使用相对地址 `/api/v1/...`，依赖 Next.js rewrites。

在相对地址模式下，需要设置仅服务端可见的 base URL：

- `BACKEND_INTERNAL_URL`（当 `NEXT_PUBLIC_API_BASE_URL` 为空时作为回退）用于 `/api/v1/:path*` 的 rewrite 目标。

## 备注
- 页面入口在 `app/` 下，修改后会热更新。
- 设计系统与 tokens 位于 `styles/`。

## 了解更多

想了解更多 Next.js：

- [Next.js Documentation](https://nextjs.org/docs) - Next.js 功能与 API 文档
- [Learn Next.js](https://nextjs.org/learn) - 交互式教程

也可以访问 [Next.js GitHub 仓库](https://github.com/vercel/next.js)。
