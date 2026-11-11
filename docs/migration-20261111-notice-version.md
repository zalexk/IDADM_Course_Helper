# user_config.notice_version 迁移 Runbook（2026-11-11）

## 背景

应用采用「公告文件 + 已读版本」方案（Plan B）：

- 公告内容存于 `data/announcements.json`，随代码部署发布；
- `public.user_config.notice_version` 记录每个用户已确认的最高公告版本；
- 登录后应用把版本高于该值的公告合并为一个弹窗，点「Got it」后写回。

本迁移只给已存在的 `public.user_config` 加一列。**不新建表、不改动任何计划表、不回填业务数据。**

## 变更清单

| 对象 | 变更 | 说明 |
|---|---|---|
| `public.user_config.notice_version` | **新增列** | `integer NOT NULL DEFAULT 0`，0 = 尚未确认任何公告 |
| 其他 6 张计划表 | 无 | 不改结构、不改数据 |
| `user_config` 存量行 | 自动取默认值 0 | 表当前为 0 行；若已有行，下次登录会看到当前保留的公告 |

## ① 预检（只读）

```sql
-- 预期 0 行：列尚不存在。
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'user_config'
  AND column_name = 'notice_version';

-- 记录迁移前的行数（用于迁移后对比；当前预期 0）。
SELECT count(*) AS row_count FROM public.user_config;
```

## ② 备份（可选）

`user_config` 只有每用户一行偏好，风险很低；如需保险，可在 Dashboard 的 Table Editor 导出 CSV，或用只读查询记录上一步的行数。不要为此新建 public schema 的快照表（可能被 API 暴露）。

## ③ 迁移（事务）

```sql
BEGIN;

ALTER TABLE public.user_config
    ADD COLUMN IF NOT EXISTS notice_version integer NOT NULL DEFAULT 0;

COMMENT ON COLUMN public.user_config.notice_version IS
    'Highest announcements.json version acknowledged by this user; 0 = none.';

COMMIT;
```

## ④ 复验（只读）

```sql
-- 预期 1 行：integer / NO / 0。
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'user_config'
  AND column_name = 'notice_version';

-- 行数应与迁移前一致。
SELECT count(*) AS row_count FROM public.user_config;
```

## ⑤ 回滚

```sql
ALTER TABLE public.user_config
    DROP COLUMN IF EXISTS notice_version;
```

旧版应用不读该列，回滚列不会影响 2nd Major 的保存与恢复；用户已读状态会丢失，之后重新弹一次公告。

## 执行记录（2026-11-11）

维护者在 Supabase SQL Editor 执行，结果：

- **③ 迁移**：`ALTER TABLE ... ADD COLUMN IF NOT EXISTS notice_version` 与 `COMMENT` 在事务中执行成功。
- **④ 复验**：`notice_version` 为 `integer`、`is_nullable = NO`、`column_default = 0`（1 行）；`user_config` 行数不变（当前 0 行）。
- **应用部署**：待执行。

## 上线顺序（重要）

**先执行 SQL，再部署新版应用。**

- 若先部署：读 `user_config` 仍能成功（`select *` 不含该列），但用户点「Got it」时写 `notice_version` 会失败并显示错误，弹窗会在下次登录再次出现。
- 先加列则部署后即可正常保存。

窗口期内旧版应用仍可正常使用：它不读 `notice_version`，也不会弹公告；`user_config` 的 `major_2nd` 不受影响。

## 手工验证清单

- [ ] 登录后弹窗出现一次，列出 `data/announcements.json` 中未读的公告（当前为 v1）；
- [ ] 点「Got it」→ 刷新页面不再弹；`user_config` 中该用户只有 1 行，`notice_version = 1`；
- [ ] 点「Later」→ 本次 session 不再弹；退出重登后再次出现；
- [ ] 换另一个账户登录 → 各自独立，不串已读状态；
- [ ] 访客不弹公告、不写 `user_config`；
- [ ] 已保存 2nd Major 的用户：点公告不会清空 `major_2nd`；改选专业也不会把 `notice_version` 重置为 0；
- [ ] 修改 `data/announcements.json` 并重新部署后，新版本只对 `notice_version` 更低的用户弹出。

## 发布新公告（日常流程）

1. 在 `data/announcements.json` 里追加 `version` 更大的条目（发布后不要修改旧条目）；
2. commit + push；
3. 重新部署（Streamlit Cloud 自动；Docker 需 rebuild；本地需重启）；
4. 用户下次登录看到；已确认旧版本的用户只会看到新版本。
