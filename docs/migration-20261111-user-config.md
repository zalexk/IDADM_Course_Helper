# user_config 表迁移 Runbook（2026-11-11）

## 背景

目前第二主修 (2nd Major) 只存在于 Streamlit `session_state`：每次打开网页、刷新、登录后都要重新选择。为让登录用户恢复上次选择，新增一张按用户保存偏好的 `user_config` 表，应用在登录后读取、在用户改选时立即 upsert。

本迁移**只新增一张空表**：不改动 6 张计划表的列、约束或任何存量行；计划数据（课程、学期、勾选）完全不受影响。

> 后续的「功能更新弹窗」也会复用本表（记录每个用户已看到的公告版本），但该功能尚未实现，本迁移**不**预建相关列；到时用 `ALTER TABLE` 补充即可。

## 变更清单

| 对象 | 变更 | 说明 |
|---|---|---|
| `public.user_config` | **新建表** | 每用户一行；`id` 主键并外键引用 `public."user"(id)` |
| `user_config.id` | `uuid PRIMARY KEY` | 与 `user.id` 一致；`ON DELETE CASCADE`，删账户时自动清理 |
| `user_config.major_2nd` | `text NULL` | 第二主修名称，取值必须属于 `app/constant.MAJOR_2nd_list`（应用层保证）；NULL = 尚未选择 |
| `user_config.updated_at` | `timestamptz NOT NULL DEFAULT now()` | 写入时间；**无触发器自动刷新**，应用不依赖该列 |

不建行、不回填：现有 19 个账户不会自动获得配置行；用户第一次选择第二主修时由应用 upsert 创建。未建行的用户在登录后看到未选择状态，与迁移前一致。

## 执行步骤（Supabase Dashboard → SQL Editor）

### ① 预检（全部符合预期才继续；任何一项不符，停止并先查明原因）

```sql
-- 1. 预期 0 行：user_config 尚不存在。
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name = 'user_config';

-- 2. 记录 user 表行数（仅作参考；本迁移不会改动它）。
SELECT count(*) AS user_count FROM public."user";

-- 3. 确认 user 表主键列（预期 id uuid）。
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'user'
  AND column_name = 'id';
```

### ② 备份（可选）

本迁移只新增空表，不重写、不删除任何存量数据，回滚只需 `DROP TABLE`，因此**不强制备份**。若想留一个还原点，可在 Dashboard → Database → Backups 确认自动备份可用并记下时间。

### ③ 迁移（事务内执行）

```sql
BEGIN;

CREATE TABLE IF NOT EXISTS public.user_config (
    id          uuid PRIMARY KEY REFERENCES public."user"(id) ON DELETE CASCADE,
    major_2nd   text,
    updated_at  timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.user_config IS
    'Per-user application preferences (currently the selected 2nd Major).';
COMMENT ON COLUMN public.user_config.major_2nd IS
    '2nd Major name, must be one of app/constant.MAJOR_2nd_list; NULL = not chosen.';

COMMIT;
```

### ④ 复验

```sql
-- 预期：3 行（id / major_2nd / updated_at），id 为 NO，updated_at 为 NO 且默认 now()
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'user_config'
ORDER BY ordinal_position;

-- 预期：row_count = 0（不预建行）
SELECT count(*) AS row_count FROM public.user_config;

-- 预期：仅 id 一个主键约束，且外键指向 public.user(id) ON DELETE CASCADE
SELECT conname, contype
FROM pg_constraint
WHERE conrelid = 'public.user_config'::regclass
ORDER BY contype;
```

### ⑤ 回滚（仅在异常时使用）

回滚顺序：**先回滚应用代码，再删表**。旧版应用不读 `user_config`，多出来的表对旧版无害；删表会丢失用户已保存的第二主修（计划数据不受影响）。

```sql
BEGIN;
DROP TABLE IF EXISTS public.user_config;
COMMIT;
```

## 执行记录（2026-11-11）

维护者在 Supabase SQL Editor 执行，结果：

- **① 预检**：`user_config` 不存在；`public."user"` 19 行；`user.id` 为 `uuid NOT NULL`。
- **③ 迁移**：建表成功（主键、`ON DELETE CASCADE` 外键、`updated_at DEFAULT now()` 均就绪）。
- **④ 复验**：
  - 列：`id uuid NO`（无默认）、`major_2nd text YES`、`updated_at timestamptz NO DEFAULT now()`；
  - `row_count = 0`（不预建行）；
  - 约束：`user_config_pkey`（`p`）与 `user_config_id_fkey`（`f`）。
- **应用部署**：待执行。

## 上线顺序（重要）

1. **先执行本 Runbook 的 SQL**（表与主键就绪）；
2. **随即部署新版应用**（commit + push）。

**不要先部署后执行 SQL**：新版 `src/storage.save_major_2nd()` 会 upsert `user_config`，表不存在时 PostgREST 返回错误，用户改选第二主修时会看到「Failed to save your 2nd Major」。读取侧（`fetch_user_config`）对错误做了降级处理，应用不会崩溃，但偏好不会保存/恢复。

窗口期内旧版应用仍可正常使用：它不读写 `user_config`。

## 迁移后人工验证清单

- [ ] 已登录用户选择 2nd Major → 刷新页面 / 重新打开 → 选择仍被恢复，课程标签页直接可用；
- [ ] 改选另一个 2nd Major → 刷新后仍是新选择（`user_config.major_2nd` 被 upsert，不产生第二行）；
- [ ] `user_config` 中该用户只有 1 行；`updated_at` 为最近写入时间；
- [ ] 换另一个账户登录 → 显示该账户自己的选择，不串号；
- [ ] 访客选择 2nd Major → 登录后按既有规则被清空，并恢复该账户已保存的选择；
- [ ] 未选过 2nd Major 的账户登录 → 下拉框保持未选择，不报错；
- [ ] 表/迁移未完成时应用仍可启动（读取降级），但保存会提示失败。
