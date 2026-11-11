# selected 标记列迁移 Runbook（2026-11-11）

## 背景

课程表新增 **Selected** 勾选列：学生可以先勾选一门课、暂不分配 Study Period，等排课完成后再填学期。为此六张计划表（`study_plan` / `pe` / `college_ge` / `four_area_ge` / `english` / `other_courses`）统一新增持久化列 `selected boolean not null default false`，同时放宽 `study_plan` 的 `study_period` 约束——该表过去要求 Study Period 非空，现在要允许「已选、未排」的 NULL 行。（`english.study_period` 在 2026-11-11 查库时已是 NULLABLE，无需变更。）

应用侧语义（`src/storage.is_selected`）：**一行算「已计划」当且仅当 Study Period 非空，或 `selected` 为 true**。已排学期的课程永远算已计划（兼容存量行与旧客户端写入的行）；只有未排学期的行才依赖 `selected`。Planner 与导出据此过滤。

**本迁移只做加法：新增列、改默认值、放宽一处 NOT NULL。不重写、不删除任何存量数据。**

## 变更清单

| 表 | 新增列 | 列定义 | 约束变更 | 说明 |
|---|---|---|---|---|
| `study_plan` | `selected` | `boolean not null`，默认 `false` | `study_period` 允许 NULL（原 NOT NULL） | 目录课程计划；导入/手工勾选但未排学期时存 NULL |
| `pe` | `selected` | 同上 | 无 | PE 录入表 |
| `college_ge` | `selected` | 同上 | 无 | College GE 录入表 |
| `four_area_ge` | `selected` | 同上 | 无 | Four Areas of GE 录入表 |
| `english` | `selected` | 同上 | 无（`study_period` 已是 NULLABLE） | 固定目录；学期本就可空 |
| `other_courses` | `selected` | 同上 | 无 | Other Courses 录入表 |

迁移分三步：

1. `ADD COLUMN selected boolean NOT NULL DEFAULT true` —— 加列时把**存量行全部回填为 true**（存量行都是旧逻辑下真实保存的计划，必须继续算已计划）；
2. `ALTER COLUMN selected SET DEFAULT false` —— 把默认值切回 false，之后应用会显式写 `selected`，不会依赖默认值；
3. `study_plan` 的 `study_period DROP NOT NULL` —— 允许「已选、未排」行（`english.study_period` 已是 NULLABLE，无需执行）。

## 执行步骤（Supabase Dashboard → SQL Editor）

### ① 预检（全部符合预期才继续；任何一项不符，停止并先查明原因）

```sql
-- 1. 当前列状态：预期 6 行，全部是 study_period，且没有 selected 列。
--    若返回 selected 行说明已经执行过本迁移，停止并核对，不要重复执行第 ③ 步。
SELECT table_name, column_name, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('study_plan', 'pe', 'college_ge',
                     'four_area_ge', 'english', 'other_courses')
  AND column_name IN ('selected', 'study_period')
ORDER BY table_name, column_name;

-- 2. 约束前置条件（2026-11-11 已查库确认）：
--    study_plan.study_period 必须是 NOT NULL（is_nullable = NO）；
--    english.study_period 已是 NULLABLE（YES），无需变更；
--    pe / college_ge / four_area_ge / other_courses 的 study_period 应为 YES。
--    若不符，说明库结构与本文档假设不同，停止并先查明原因。

-- 3. 基线行数（记下来，第 ④ 步复验时逐一对比；迁移不应改变任何行的数量）
SELECT 'study_plan' AS table_name, count(*) FROM study_plan
UNION ALL SELECT 'pe',            count(*) FROM pe
UNION ALL SELECT 'college_ge',    count(*) FROM college_ge
UNION ALL SELECT 'four_area_ge',  count(*) FROM four_area_ge
UNION ALL SELECT 'english',       count(*) FROM english
UNION ALL SELECT 'other_courses', count(*) FROM other_courses;
```

### ② 备份（可选）与行数基线（必做）

```sql
-- 方式 A（可选）：Supabase Dashboard → Database → Backups 确认最近备份可用并记下时间；
--   也可用 SQL 快照表或 CSV 导出。本迁移只改 schema、不重写存量行，回滚不依赖备份，
--   备份用于防操作失误（跑错项目/语句），不是恢复迁移数据的必需条件。

-- 方式 B（必做，已在第 ① 步完成）：记下第 ① 步第 3 条的六张表行数基线，第 ④ 步逐项对比。
--   注意：行数基线是迁移正确性校验，不是备份。
```

### ③ 迁移（事务内执行）

```sql
BEGIN;

-- 六张表新增 selected 列：NOT NULL DEFAULT true 会把存量行回填为 true
-- （存量行都是旧逻辑下真实保存的计划，必须保持「已计划」）。
ALTER TABLE study_plan    ADD COLUMN selected boolean NOT NULL DEFAULT true;
ALTER TABLE pe            ADD COLUMN selected boolean NOT NULL DEFAULT true;
ALTER TABLE college_ge    ADD COLUMN selected boolean NOT NULL DEFAULT true;
ALTER TABLE four_area_ge  ADD COLUMN selected boolean NOT NULL DEFAULT true;
ALTER TABLE english       ADD COLUMN selected boolean NOT NULL DEFAULT true;
ALTER TABLE other_courses ADD COLUMN selected boolean NOT NULL DEFAULT true;

-- 默认值切回 false：此后应用必须显式写 selected，不再依赖列默认值。
ALTER TABLE study_plan    ALTER COLUMN selected SET DEFAULT false;
ALTER TABLE pe            ALTER COLUMN selected SET DEFAULT false;
ALTER TABLE college_ge    ALTER COLUMN selected SET DEFAULT false;
ALTER TABLE four_area_ge  ALTER COLUMN selected SET DEFAULT false;
ALTER TABLE english       ALTER COLUMN selected SET DEFAULT false;
ALTER TABLE other_courses ALTER COLUMN selected SET DEFAULT false;

-- 放开 study_plan 的学期约束：允许「已选、未排学期」的 NULL 行。
-- （english.study_period 已是 NULLABLE，无需 DROP NOT NULL。）
ALTER TABLE study_plan ALTER COLUMN study_period DROP NOT NULL;

COMMIT;
```

### ④ 复验

```sql
-- 预期：6 行，全部是 selected，is_nullable = NO，column_default = false
SELECT table_name, column_name, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('study_plan', 'pe', 'college_ge',
                     'four_area_ge', 'english', 'other_courses')
  AND column_name = 'selected'
ORDER BY table_name;

-- 预期：study_plan 的 is_nullable = YES；english 本来就是 YES；其余四表仍为 YES
SELECT table_name, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('study_plan', 'pe', 'college_ge',
                     'four_area_ge', 'english', 'other_courses')
  AND column_name = 'study_period'
ORDER BY table_name;

-- 预期：各表 total 与第 ① 步基线完全一致；selected_true = total
-- （加列默认值把存量行全部回填为 true）
SELECT 'study_plan' AS table_name, count(*) AS total,
       count(*) FILTER (WHERE selected) AS selected_true FROM study_plan
UNION ALL SELECT 'pe',            count(*), count(*) FILTER (WHERE selected) FROM pe
UNION ALL SELECT 'college_ge',    count(*), count(*) FILTER (WHERE selected) FROM college_ge
UNION ALL SELECT 'four_area_ge',  count(*), count(*) FILTER (WHERE selected) FROM four_area_ge
UNION ALL SELECT 'english',       count(*), count(*) FILTER (WHERE selected) FROM english
UNION ALL SELECT 'other_courses', count(*), count(*) FILTER (WHERE selected) FROM other_courses;
```

### ⑤ 回滚（仅在异常时使用）

回滚顺序：**先回滚应用代码，再按需回滚数据库**。旧版应用不读 `selected` 列、也不会往 `study_plan` / `english` 写 NULL 学期，因此多出来的列与放宽的约束对旧版无害；但新版产生的「已选、未排」行（`study_period IS NULL AND selected = true`）在旧版页面上不可见，Planner 仍会按学期聚合——rollback 前先确认这类行的去留。

```sql
-- 1) 可选：清理新版产生、旧版无法展示的「已选、未排」行
--    （先 SELECT 核对；决定保留则跳过本步）
SELECT 'study_plan' AS table_name, id, course_id FROM study_plan
WHERE study_period IS NULL AND selected
UNION ALL SELECT 'english', id, course_id FROM english
WHERE study_period IS NULL AND selected;

-- 2) 恢复 study_plan 的 NOT NULL 约束（仅当已无 NULL 行，否则此步会失败）
--    english.study_period 已是 NULLABLE，无需恢复。先决定 NULL 行的去留：
--    删除，或逐行人工补 Study Period（不要用固定学期批量填充），确认
--    count(*) FILTER (WHERE study_period IS NULL) = 0 后执行：
ALTER TABLE study_plan ALTER COLUMN study_period SET NOT NULL;

-- 3) 删除 selected 列（schema 回到迁移前；会丢失该列的勾选信息）
BEGIN;
ALTER TABLE study_plan    DROP COLUMN selected;
ALTER TABLE pe            DROP COLUMN selected;
ALTER TABLE college_ge    DROP COLUMN selected;
ALTER TABLE four_area_ge  DROP COLUMN selected;
ALTER TABLE english       DROP COLUMN selected;
ALTER TABLE other_courses DROP COLUMN selected;
COMMIT;
```

## 执行记录（2026-11-11）

维护者在 Supabase SQL Editor 执行，结果：

- **① 预检**：`selected` 列不存在；`study_plan.study_period` 为 `NO`，其余五表为 `YES`；行数基线 study_plan 337 / pe 32 / college_ge 28 / four_area_ge 12 / english 20 / other_courses 4。
- **③ 迁移**：事务执行成功（六表加列 → 切默认值 → `study_plan.study_period DROP NOT NULL`）。
- **④ 复验**：
  - `selected` 在六表均存在，`is_nullable = NO`、`column_default = false`（共 6 行）；
  - 六表 `study_period` 均为 `YES`；
  - 行数与基线完全一致，且每表 `selected_true = total`（迁移把存量行全部回填为 `true`）。
- **应用部署**：待执行（窗口期内旧版应用仍可用；SQL 已就绪，新版代码可随时上线）。

## 上线顺序（重要）

1. **先执行本 Runbook 的 SQL**（列、默认值、NOT NULL 状态全部就绪）；
2. **随即部署新版应用**（commit + push），窗口压到最短。

**严禁先部署后执行 SQL**：新版 `src/storage.py` 的每条写入都会带 `selected` 字段，列不存在时 PostgREST 会拒绝写入——所有保存、勾选、导入都会报错，用户数据无法落库。

窗口期内旧版应用仍可正常使用：新列有默认值（旧版写入的行 `selected` 按默认值处理），旧版也从不写 NULL 学期，不违反保留的约束。窗口内旧版保存的「未填学期」录入表草稿会得到 `selected = false`，这正是新版「草稿不算已计划」的语义，无需额外处理。

## 迁移后人工验证清单

- [ ] 存量用户视角：各标签页课程与 Study Period 与迁移前一致，Planner 总学分无变化（存量行 `selected = true`，已排课程也仍按学期计数，不重复累加）；
- [ ] 勾选一门课但清空 Study Period → 保存后刷新仍在（`selected = true`、`study_period = NULL`），Planner 计入该课；
- [ ] 取消勾选 → 该课从计划消失（`study_plan` 行被删除；录入表行保留为草稿、不计入计划）；
- [ ] Planner 导出 PDF / Word：存在「已选、未排学期」课程时，末尾出现 "Selected Courses (No Study Period)" 段并给出 Total Selected Credits；全部课程都已排学期时没有该段；
- [ ] 课程导入：导入的课程写入即 `selected = true`；学习计划类课程未填 Study Period 时被跳过并提示「set a Study Period to import it」，录入表课程未填学期仍可保存；
- [ ] 旧版应用（迁移后、新版上线前的窗口）保存不报错。
