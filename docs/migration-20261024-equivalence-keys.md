# study_plan 课程主键迁移 Runbook（2026-10-24）

## 背景

`data/equivalence_courses.csv` 已对齐官方 2025-26 新版课程对应表（8 行改动，详见 `../Equivalent-Course-CSV-Audit.md` 审计）。目录表的数据库主键由 `_course_key()` 决定（`src/data_retrieval.py`）：**SZ 课程一旦有了 HK 等价映射，主键就从 SZ 码切换为 HK 码**。因此部分存量 `study_plan` 行的主键需要同步迁移，否则：

- 受影响用户的 Study Period 从页面消失（召回按 key 精确匹配）；
- Financial Engineering 两位用户的 Required Courses 从 18 学分/已完成 变为 15 学分/未完成；
- 若用户在页面上重新选择学期，会以新 key 插入新行而旧行残留，Planner 将同一门课重复计分。

**本迁移只写 `study_plan` 表，共 2 条 UPDATE，预期影响 5 行 / 5 个用户。**

## 主键变更清单

| 页面 / 课程 | 旧 key（存量行） | 新 key | 预期存量行数（2026-10-19 审计） |
|---|---|---|---:|
| FE Required、IDA 选修（多专业分组）的 `FIN3210` | `FIN3210` | `SEEM2520` | 2 行 / 2 用户 |
| FE / CSE / Statistics (SZ) 三个页面的 `CSC3170` | `CSC3170` | `CSCI3170` | 3 行 / 3 用户 |
| ECE 的 `CSC4001` | `IERG3080` | `CSCI3100`（CSV 已改为单一代表，不再使用复合键） | 0 行 |
| Math & Applied 的 `MAT3220` | `MAT3220` | `MATH4230` | 0 行 |
| Statistics (SZ) 的 `MAT2002` | `MAT2002` | `MATH3270` | 0 行 |

后三行预期零存量，仅列入预检查证；若预检发现非零，按同样模式补充 UPDATE。

> 说明：迁移后 `SEEM2520` 同时是 FE Required 与 IDA 选修表的 key——这正是 `_course_key` 的设计意图（同一门课跨标签页共享同一行 study_period）。

## 执行步骤（Supabase Dashboard → SQL Editor）

### ① 预检（全部符合预期才继续；任何一项不符，停止并先查明原因）

```sql
-- 1. 受影响存量行：预期共 5 行（CSC3170 ×3、FIN3210 ×2）
SELECT * FROM study_plan
WHERE course_id IN ('CSC3170', 'FIN3210')
ORDER BY course_id, id;

-- 2. 目标键冲突预检：预期 0 行
--    （(id, course_id) 是唯一约束；若同一用户已有目标键行，UPDATE 会失败，需先人工合并）
SELECT * FROM study_plan
WHERE course_id IN ('CSCI3170', 'SEEM2520')
  AND id IN (SELECT id FROM study_plan WHERE course_id IN ('CSC3170', 'FIN3210'));

-- 3. 其他迁移面代码复核：预期每个代码 0 行
--    （最后两个是 major_course_list.json 里 Information Engineering 的历史
--     「二选一」复合目录项，与本次迁移无关；若非 0 属遗留存量，记录待后续清理）
SELECT course_id, count(*) FROM study_plan
WHERE course_id IN ('MAT2002', 'MAT3220', 'MATH3270', 'MATH4230',
                    'CSC4001', 'IERG3080', 'CSCI3100',
                    'IERG3080/ CSCI3100',
                    'IERG4004/FTEC4004', 'IERG4130/CSCI4130')
GROUP BY course_id;

-- 4. 录入表污染扫描：预期各 0 行（这些表存用户手填的 GE/PE/英语课）
SELECT 'pe' AS src, id, course_id FROM pe           WHERE course_id ILIKE '%CSC3170%' OR course_id ILIKE '%FIN3210%'
UNION ALL
SELECT 'college_ge', id, course_id FROM college_ge  WHERE course_id ILIKE '%CSC3170%' OR course_id ILIKE '%FIN3210%'
UNION ALL
SELECT 'four_area_ge', id, course_id FROM four_area_ge WHERE course_id ILIKE '%CSC3170%' OR course_id ILIKE '%FIN3210%'
UNION ALL
SELECT 'english', id, course_id FROM english         WHERE course_id ILIKE '%CSC3170%' OR course_id ILIKE '%FIN3210%';
```

### ② 备份（二选一，推荐前者）

```sql
-- 方式 A：建备份表（稳定运行约两周后可 DROP）
CREATE TABLE study_plan_backup_20261024 AS
SELECT * FROM study_plan WHERE course_id IN ('CSC3170', 'FIN3210');
```

方式 B：运行预检第 1 条查询，在 SQL Editor 结果区右键 Export CSV 存档。

### ③ 迁移（事务内执行，核对提示的 UPDATE 行数）

```sql
BEGIN;

UPDATE study_plan SET course_id = 'CSCI3170' WHERE course_id = 'CSC3170';  -- 预期 UPDATE 3
UPDATE study_plan SET course_id = 'SEEM2520' WHERE course_id = 'FIN3210';  -- 预期 UPDATE 2

COMMIT;
```

### ④ 复验

```sql
-- 预期：CSCI3170 = 3、SEEM2520 = 2，CSC3170 / FIN3210 不再出现
SELECT course_id, count(*) FROM study_plan
WHERE course_id IN ('CSC3170', 'FIN3210', 'CSCI3170', 'SEEM2520')
GROUP BY course_id;

-- 预期：与迁移前相同（本次审计基线 297）
SELECT count(*) FROM study_plan;
```

### ⑤ 回滚（仅在异常时使用）

```sql
-- 注意：若迁移后已有用户以新 key 重新保存过，逆向 UPDATE 会撞唯一约束，
-- 需先按备份表人工去重。
UPDATE study_plan SET course_id = 'CSC3170'
WHERE course_id = 'CSCI3170'
  AND id IN (SELECT id FROM study_plan_backup_20261024 WHERE course_id = 'CSC3170');

UPDATE study_plan SET course_id = 'FIN3210'
WHERE course_id = 'SEEM2520'
  AND id IN (SELECT id FROM study_plan_backup_20261024 WHERE course_id = 'FIN3210');
```

## 上线顺序（重要）

1. **先执行本 Runbook 的 SQL**（UPDATE 完成）；
2. **随即部署新版应用**（commit + push 新 `equivalence_courses.csv`），窗口压到最短。

窗口期内这 5 行在旧版页面同样显示为空（与不做迁移的症状一致，不会更糟）。**严禁先部署后 UPDATE**：窗口内用户在页面上重新选择学期会以新 key 产生新行，之后 UPDATE 将撞 `(id, course_id)` 唯一约束而失败。

## 迁移后人工验证清单

- [ ] FE 二专用户视角：Required Courses 恢复 18 学分 / 已完成，`SEEM2520 / FIN3210` 行的 Study Period 回填；
- [ ] CSE 二专用户视角：Required Courses 恢复（`CSCI3170 / CSC3170` 行 Study Period 回填）;
- [ ] Statistics (SZ) 二专用户视角：`CSC3170` 选修行 Study Period 回填；
- [ ] Planner 标签页：上述学期的总学分无重复累加（同一门课只计一次）。

## 遗留问题（另行处理，不在本次范围）

- 存量复合键 `CSCI3320/ MATH3320/ STAT4001`（2 行）的清理，及 CSV 复合行重构为「主映射 + 别名」结构；
- `major_course_list.json` 中 Information Engineering 的两个「二选一」复合目录项 `IERG4004/FTEC4004`、`IERG4130/CSCI4130`（本次回归测试 `TestCatalogueKeyIntegrity` 新发现，按 HK 码原样充当主键）；
- 导入路径 `canonical_course_id` 与页面 per-major key 的不一致（如 `CSC3170` 导入时规范化为 `SEEM3550`，而页面为 `CSCI3170`）;
- honours 备选课（`MAT1011` / `MAT1012` / `STA2002H` 等）按既定「单一代表」策略继续不识别。
