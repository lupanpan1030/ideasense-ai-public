# 种子数据

用途：本地/开发环境的基础数据。可手动执行或通过 `database/scripts/reset_db.py`。

建议：
- 数据保持幂等
- 不要包含生产敏感信息
- 在项目工具链里清楚标注执行方式

主脚本：
- `database/seeds/seed_dev.sql`
- 各业务流脚本位于 `database/seeds/flows/`，由主脚本引用。

前置条件：
- 先导入题库（seed 会使用 `question_bank_versions` 与 `question_bank_questions`）。

使用 psql：
```
psql "postgres://USER:PASSWORD@HOST:PORT/DBNAME" -f database/seeds/seed_dev.sql
```

单独执行某个流程：
```
psql "postgres://USER:PASSWORD@HOST:PORT/DBNAME" -f database/seeds/flows/<flow>/<flow>_seed.sql
```

开发超管账号：
- Email: `superadmin@demo.local`
- Password: `12345678`
- 密码存储在 `user_identities`，使用 `crypt(..., gen_salt('bf'))`（pgcrypto/bcrypt）。

DEV 直通（用于管理端调试）：
- 不导入题库时，先执行 `database/seeds/flows/org/org_seed.sql`。
- 设置 `DEV_AUTH_BYPASS=1`。
- 设置 `DEV_ORG_ID=11111111-1111-1111-1111-111111111111`。
- 设置 `DEV_USER_ID=99999999-9999-9999-9999-999999999999`（owner）或 `aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa`（admin）。

流程概览：
- `org/`: 组织、用户、成员关系（含 invited/removed）。
- `auth/`: 本地身份（含 disabled 账号用于失败场景）。
- `cohorts/`: 班级 + 成员关系（含 removed）。
- `assignments/`: 导师分配（active/pending/revoked）。
- `projects/`: 项目、运行态、题目实例（answered/invalid/needs_info）。
- `evidence/`: 对话消息 + 项目状态/事件。
- `outputs/`: 阶段评估 + 报告 + 批注（draft/final/confirmed）。
- `evaluations/`: 评分规则 + 答案/消息评估（高低分）。
- `assets/`: 文档 + 通知（uploaded/failed/indexed，read/unread）。
- `ops/`: 后台任务 + 分析/审计事件（succeeded/failed/running）。
