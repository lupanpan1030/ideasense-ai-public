# 迁移（Migrations）

用途：有序的 SQL 迁移脚本，是结构的唯一真实来源。

## 基线迁移
- `000_baseline_*.sql` 为合并后的 schema 基线快照。
- `001_seed_core_*.sql` 写入必要的基础数据（例如默认评估量表）。
- 旧迁移已归档到 `database/migrations_legacy/`，不再执行。

## 命名规则
- `NNN_description_YYYYMMDDHHMMSS.sql`

## 如何新增迁移
- 使用下一个序号新建文件。
- 不要修改历史迁移；有变更就新增一条。
- 变更后生成新的 schema 快照。

相关：
- 快照：`database/schema/schema.sql`
- 生成脚本：`database/scripts/generate_schema_snapshot.py`
- 根文档：`database/README.md`
