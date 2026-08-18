# Study Period 持久化：规范课程 Key 方案

> 状态：已实施（`_course_key` + `data_on_change` index 身份 + ucore index 注入）。决策冻结如前，本文档为实施参考。DB 存量迁移（§4）与浏览器手测（§7.4）待执行。

## 0. 背景与决策记录

### 现状问题
1. **DB key 用显示文本**（`"课号 | 标题"`）：`data_on_change` 以 `"CUHK"` 列值为 `course_id`。
2. **Unavailable 冲突**：无 CUHK 等价课的行显示 `"Unavailable"`，多门课共享同一 key → upsert 互相覆盖。实测：FE 选修 9 门、CSE 选修 11 门 Unavailable（University Core 为 0，当前唯一接入页面暂未触发）。
3. **跨表污染**：`fetch_data` 不按 major/类别过滤，`"Unavailable"` key 跨 tab 共享。
4. **身份劫持**：`ucore.py` 传 `disabled_col=[]`，"CUHK" 列可编辑，用户改显示格即篡改 `course_id`。
5. **campus 对齐耦合**：读回 key 依赖 `campus` 参数与显示列一致，传错静默返回全空。

### 需求与决策
| 编号 | 内容 | 决策 |
|---|---|---|
| 要求① | 同一门课（含跨校区等价课，如 ELEG2201/ECE2050）在不同 tab 的 study period 一致 | 采纳，作为 key 设计核心 |
| R1 | 同 session 跨 tab 陈旧显示（见 §6） | **接受**，文档化，刷新恢复 |
| R2 | 4 门课身份分裂（DDA3020、CSC3180、DDA4210、CSC3050） | **有意差异**（per-major 等价是刻意的），CSV 不动，分裂即正确语义 |

## 1. 核心定义：规范课程身份（canonical key）

DB 主键语义：`(user_id, canonical_key)` 唯一确定一门课。

```python
def _course_key(context, major, cid) -> str:
    if determine_campus(cid) == "hk":
        return cid                                  # ① HK 课：自身即规范
    try:
        return convert_course_id(context, major, cid)  # ② SZ 课：转 HK 等价课号
    except InfoMissingError:
        return cid                                  # ③ 无等价：SZ 课号回退（本身唯一）
```

- 分支②实现要求①的跨校区身份合并；转换用 **per-major** bidict（R2 决策：不全局合并）。
- 分支③根除 Unavailable 冲突。

### 已验证事实（基于当前数据扫描）
- 全部 major × 类别表内 canonical key **零重复** → 可作唯一键。
- 48 门课在不同列表中以不同课号出现 → 原始课号不能直接当 key。
- 4 门课身份分裂（R2 已确认为有意）：
  - `DDA3020` → `CSCI3320` / `STAT4001`（两 major 各认不同等价，映射冲突，保留）
  - `CSC3180` → `CSCI3230` / 自身；`DDA4210` → `RMSC4002` / 自身；`CSC3050` → `AIST3020` / 自身（等价缺口，保留）

## 2. 数据流

**写入**：`course_list` → 页面批量算 `_course_key` 设为 `df.index`（`hide_index=True`，不可见）→ 用户编辑 → `data_on_change` 以 `df.iloc[i].name` 为 `course_id` upsert。

**读取**：`fetch_data(user_id)` → `{course_id: study_period}` 字典 → 按 `course_list` 顺序 `saved.get(_course_key(cid), "")` → 初始 df。

写读两侧使用同一函数、同一份 course_list、同一顺序 → key 必然对齐；campus 对齐耦合随之消除。

## 3. 文件改动清单

### 3.1 `src/data_retrieval.py`
- **新增** `_course_key(context, major, cid) -> str`（§1）。
- **`show_course_info` 的 `study_period` 分支**改为：
  ```python
  if request_type == "study_period":
      if not (user_id := st.session_state.get("user_id")):
          return ["" for _ in courses]
      saved = {row["course_id"]: row["study_period"] for row in fetch_data(user_id)}
      return [saved.get(_course_key(context, major, cid), "") for cid in courses]
  ```
  删除"campus must match"注释；`campus` 参数不再参与查库。
- `_course_label()` 保留，职责收窄为显示列文本（"CUHK"/"CUHKSZ" 列）。

### 3.2 `app/ucore.py`
- 建表加 index：
  ```python
  course_table = pd.DataFrame(
      {...},
      index=[_course_key(context, "University Core", c) for c in course_list],
  )
  ```
- 其余不动（`hide_index=True` 已在 `table_editor` 设置，UI 零变化）。

### 3.3 `src/storage.py` — `data_on_change`
- edited/deleted 行身份取自 index 标签：
  ```python
  "course_id": df.iloc[int(index)].name          # edited
  delete_data(user_id, df.iloc[int(index)].name) # deleted
  ```
- **入口防呆校验**（空表安全版）：
  ```python
  if len(df.index) > 0 and not isinstance(df.index[0], str):
      st.error("Table index must carry course keys.")
      return
  ```
  防止未来页面忘传 index 退回 RangeIndex，把行号当 `course_id` 静默写库。
- added 行（当前 `num_of_rows="fixed"` 不触发）：保持回退为用户输入文本。
- 附带修复：用户编辑 "CUHK" 显示格不再影响 `course_id`（身份劫持消除）；对 "CUHK"/"CUHKSZ"/"Credits" 列的编辑不产生 DB 写入（仅 "Study Period" 变化触发 upsert——实现时按 `changes` 是否含目标列判断，或保持现状全量 upsert，幂等无害）。

## 4. DB 迁移（一次性）

```sql
-- ① 旧 label key 的课号部分恰好等于 canonical key（label 用转换后课号）
UPDATE study_plan SET course_id = split_part(course_id, ' | ', 1)
WHERE course_id LIKE '% | %';

-- ② 'Unavailable' 存量行：无法自动归属，人工查看后改 key 或删除
SELECT * FROM study_plan WHERE course_id = 'Unavailable';
```

**执行顺序**：迁移 ① → 部署代码 → 立即复跑迁移 ①（收敛窗口期内旧代码写入的 label key 行）。

## 5. 边界行为

| 场景 | 行为 |
|---|---|
| 同课出现两个 tab | 共用一个 DB 行；改任一 tab，另一 tab 下次 rerun 显示新值（要求①） |
| 4 门有意分裂课 | 各 tab 独立身份，study period 各自维护（R2） |
| Unavailable 课 | key = 原始 SZ 课号，互不覆盖、不跨表污染 |
| 编辑 "CUHK" 显示格 | 不影响 `course_id`，不产生有意义的 DB 变更 |
| 访客 | `data_on_change` 提前 return；`study_period` 分支返回全 `""`，零 DB 交互 |
| dynamic 新增行（当前未启用） | 字符串 index 下 Streamlit 跳过新增行（源码 `_apply_row_additions` 只支持整数 index）；固定目录表不需要 |
| 空表类别 | 校验 `len(df.index) > 0` 短路，不抛 `IndexError` |

## 6. 已接受风险登记

| 编号 | 风险 | 状态 |
|---|---|---|
| R1 | 同 session 跨 tab 陈旧显示：tab B 对该课有旧 `edited_rows` 时，tab A 的更新在 tab B 不显示，刷新恢复 | **接受**，不实现清理逻辑 |
| R2 | 4 门课身份分裂 | **有意差异**，保留 |
| R3 | 错误等价行（疑似 `MKT4120→MKTG3010`）可能合并两门不同的课 | 人工核对 CSV，与本次改动解耦 |
| R4 | key 锚定可变数据：`equivalence_courses.csv` 更新后存量 key 可能失配 | 每次 CSV 更新后跑孤儿 key 检测（`SELECT course_id` 对照当前数据重现），人工再迁移 |
| R5 | 访客编辑残留：登录后 guest 的 `edited_rows` 仍覆盖显示，下次编辑触发补存自愈 | 接受 |
| R7 | 迁移/部署窗口的双行 | §4 复跑迁移收敛 |
| R8 | `'Unavailable'` 存量行 | 人工处理 |
| R9 | 每 rerun 每 tab 一次 `fetch_data` | 暂不优化；必要时 `st.cache_data` + 保存后清缓存 |
| R10 | 同用户多浏览器标签 last-write-wins | 接受 |
| R11 | 无测试套件 | 本次以冒烟脚本验证；建议后续补 `_course_key`/`data_on_change` 最小单测 |

## 7. 验证计划（实施后逐项执行）

1. `py_compile` 三个改动文件。
2. 冒烟（venv 脚本，mock `fetch_data` + `st.session_state`）：
   - 访客 → 全 `""`；
   - 已登录 → 仅 DB 有记录的课程回显，长度/顺序与 `course_list` 一致；
   - Unavailable 课 → key 为原始 SZ 课号，不与它课共享；
   - 跨校区等价课（ECE2050）→ key 为 `ELEG2201`，与 HK 课同 key（要求①）；
   - index 防呆：RangeIndex df 触发 `st.error` 且不写库。
3. 迁移演练：造 label key 行 → 跑 §4 SQL → 新代码读回一致。
4. 浏览器手动：登录 → UCORE tab 设 study period → 刷新 → 回显；切 tab 渲染无异常。

## 8. 实施顺序

1. `src/data_retrieval.py`：`_course_key` + `study_period` 分支改造
2. `src/storage.py`：`data_on_change` 身份来源 + 防呆校验
3. `app/ucore.py`：index 注入
4. 冒烟验证（§7.1–7.2）
5. DB 迁移 ① → 部署 → 复跑 ①，人工处理 ②
6. 浏览器手测（§7.4）
