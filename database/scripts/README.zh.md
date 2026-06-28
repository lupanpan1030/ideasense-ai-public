# 脚本

用途：数据库初始化与维护工具。
托管数据库（Neon/Render 等）建议使用 `--managed-db`，跳过角色授权并在导入题库时临时放开 FORCE RLS。
手动 psql 调试时可执行 `database/scripts/with_system_actor.sql`（设置 system 上下文）。

## bootstrap_db.py
创建数据库、运行迁移、应用角色、导入题库，并生成结构快照。

示例：
```
DATABASE_URL_ADMIN=... python database/scripts/bootstrap_db.py
```

常用参数：
- `--db-name`
- `--env-file`
- `--managed-db`、`--skip-roles`、`--skip-migrations`、`--skip-question-bank`、`--skip-schema`
- `--mark-existing`（仅标记迁移已执行，不实际运行迁移）

## reset_db.py
删库重建，运行迁移、应用角色、导入题库，再执行种子数据。

示例：
```
DATABASE_URL_ADMIN=... python database/scripts/reset_db.py --db-name ideasense_ai_dev
```

常用参数：
- `--managed-db`、`--skip-roles`、`--skip-question-bank`、`--skip-seed`、`--skip-schema`
- `--question-bank-yaml`、`--seed-file`

## import_question_bank.py
将 YAML 题库导入 `question_bank_versions` 和 `question_bank_questions`。

示例：
```
python database/scripts/import_question_bank.py --dsn "<dsn>" --yaml resources/question_bank.example.yaml
```

私有部署可以显式传入私有生产题库 YAML。公开导出版本应使用
`resources/question_bank.example.yaml`。

## generate_schema_snapshot.py
把 migrations 拼接成 `database/schema/schema.sql`。

示例：
```
python database/scripts/generate_schema_snapshot.py
```

## rls_roles.sql
运行时/worker 角色与授权配置（禁止 BYPASSRLS）。
位置：`database/roles/rls_roles.sql`。

## with_system_actor.sql
设置 `app.actor_type=system`，便于在 RLS 下调试。
