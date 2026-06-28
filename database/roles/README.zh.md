# 角色与权限

运行时/worker 角色与授权定义。

- `rls_roles.sql`：为自建 Postgres 创建角色与授权。
- 托管数据库可能不允许 `ALTER ROLE ... BYPASSRLS`，请使用 `--managed-db` 跳过。
