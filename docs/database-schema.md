# Supabase 数据库 Schema

> 最后核验：2026-11-11。核验方式：使用 `.streamlit/secrets.toml` 中的 `SUPABASE_URL` / `SUPABASE_KEY`，通过 PostgREST OpenAPI（`GET /rest/v1/`）与只读 `SELECT` 查询。**未做任何写操作**；同日的 `selected` 列迁移由维护者在 Supabase SQL Editor 执行，执行记录见 [migration-20261111-selected-flag.md](migration-20261111-selected-flag.md)。同日新增的 `user_config` 表已由维护者执行并复验（0 行，懒创建），见 [migration-20261111-user-config.md](migration-20261111-user-config.md)；同日的 `notice_version` 列迁移已由维护者执行并复验（`integer NOT NULL DEFAULT 0`），见 [migration-20261111-notice-version.md](migration-20261111-notice-version.md)。
>
> 结构或语义变更后请同步更新本文件，并在 `docs/` 新增对应迁移 Runbook（参考 [migration-20261024-equivalence-keys.md](migration-20261024-equivalence-keys.md)、[migration-20261111-selected-flag.md](migration-20261111-selected-flag.md)、[migration-20261111-user-config.md](migration-20261111-user-config.md)、[migration-20261111-notice-version.md](migration-20261111-notice-version.md)）。

## 1. 访问方式与安全边界

| 项目 | 说明 |
|---|---|
| 项目 | 单一 Supabase 项目；具体 host / key 只存在于 `.streamlit/secrets.toml`（已 gitignore，勿提交、勿写入文档） |
| 应用访问 | `src/storage.py` 用 `st.secrets` 构造 Supabase client；`src/auth.py` 查询 `user` 表 |
| 只读排查 | 可经 PostgREST `GET /rest/v1/<table>?select=...` 查询（带 `apikey` / `Authorization` 头）；计数用 `Prefer: count=exact` |
| 写操作 | **应用运行时**通过 `upsert_data` / `delete_data` 写入；**人工/AI 排查时禁止直接写库**，schema 变更一律先写成 `docs/migration-*.md` Runbook，由维护者在 Supabase Dashboard → SQL Editor 执行 |
| 敏感字段 | `user.password` 存 PBKDF2-HMAC-SHA256 哈希（格式 `pbkdf2_sha256$<iterations>$<salt_hex>$<digest_hex>`），任何文档、日志、截图都不得包含该列的值 |

## 2. 表总览

| 表 | 行数（2026-11-11） | 用途 | 主键 |
|---|---:|---|---|
| `user` | 19 | 账户（用户名 + 密码哈希） | `id` |
| `user_config` | 0 | 每用户偏好（第二主修；后续可扩展公告已读版本） | `id` |
| `study_plan` | 337 | 目录课程的学习计划（University Core / IDA / 2nd Major / Chinese Language 等） | `(id, course_id)` |
| `pe` | 32 | 体育（自由录入） | `(id, course_id)` |
| `college_ge` | 28 | 书院通识（自由录入） | `(id, course_id)` |
| `four_area_ge` | 12 | 四范围通识（自由录入） | `(id, course_id)` |
| `english` | 20 | 英文语文课程（固定目录，按学院） | `(id, course_id)` |
| `other_courses` | 4 | 不在 study scheme 内、但计划修读的课程 | `(id, course_id)` |
| `chinese` | 0 | **遗留表**，应用不使用；中文课程实际写 `study_plan` | `(id, course_id)` |
| `study_plan_backup_20261024` | 5 | 2026-10-24 主键迁移前的手工备份，无约束，勿读写 | 无 |

行数只作快照参考，会随用户使用变化。2026-11-11 的 `selected` 迁移未改变任何表行数（六表仍为 337/32/28/12/20/4），存量行回填 `selected = true`。`user_config` 已于 2026-11-11 创建，当前 0 行（应用懒创建，用户首次选择后才有一行）。

## 3. 通用约定

- **`(id, course_id)` 复合主键**：`id` 是 `auth`/`user` 的用户 UUID；`course_id` 是课程身份。应用 `upsert_data` 的 `on_conflict='id,course_id'` 必须与之一致。
- **`course_id` 的两种口径**：
  - 目录表（`study_plan`、`english`）：规范化课程码（HK 码；SZ 码经 `_course_key()` 映射为 HK 等价码）。详见 `src/data_retrieval._course_key()`。
  - 自由录入表（`pe` / `college_ge` / `four_area_ge` / `other_courses`）：用户手填的整格文本 `CODE Title`（不是裸课程码），因此这类表的 `course_id` 不能与目录表直接互认。
- **`study_period`**：取自 `app/constant.py` 的 `STUDY_CAMPUS` 键，例如 `Year 1 Sem 1`、`Year 3 Summer (CUHKSZ)`。空值含义见各表说明；`study_plan` 自 2026-11-11 迁移起允许 NULL（「已选、未排学期」）。
- **`credits`**：只有四张自由录入表持久化学分（用户手填）；目录表的学分始终由 `data/course_list.csv` 推导，不入库。
- **`selected`（2026-11-11 已迁移）**：六张计划表均有 `boolean NOT NULL DEFAULT false`；迁移时存量行回填为 `true`。应用判定「已计划」用 `src/storage.is_selected(row)`：`selected = true` **或** `study_period` 非空（学期优先，兼容旧客户端/存量行）。见 [migration-20261111-selected-flag.md](migration-20261111-selected-flag.md)。
- **`user_config`（2026-11-11 已创建）**：每用户一行（`id` 主键 = `user.id`，`ON DELETE CASCADE`），`major_2nd text NULL` 保存第二主修（取值必须属于 `app/constant.MAJOR_2nd_list`，应用层保证），`notice_version integer NOT NULL DEFAULT 0` 保存已确认的最高公告版本（0 = 未确认；见 `data/announcements.json` 与 [migration-20261111-notice-version.md](migration-20261111-notice-version.md)）。应用懒创建：用户第一次选择时才 upsert，不预建行。读取失败时应用降级为未选择，不崩溃。
- **`updated_at`**：多数表默认 `now()`，但 PostgREST 看不到触发器，是否自动更新需在 Dashboard 确认（见第 6 节）。

## 4. 逐表字段

类型与默认值来自 PostgREST OpenAPI 的 `definitions`；`NOT NULL` 结合 `required` 列表与只读查询确认，`selected` 列的状态结合 2026-11-11 迁移复验结果确认；`notice_version` 已由同日迁移新增并经维护者复验（`integer NOT NULL DEFAULT 0`）。

### `user`

| 列 | 类型 | NULL | 默认 | 说明 |
|---|---|---|---|---|
| `id` | `uuid` | NO | `gen_random_uuid()` | 主键；同时被计划表的 `id` 外键引用 |
| `created_at` | `timestamptz` | NO | `now()` | 注册时间 |
| `name` | `text` | NO | — | 用户名（应用层 strip 后使用） |
| `password` | `text` | YES | — | PBKDF2 哈希；敏感，勿导出 |

### `user_config`

每用户一行的偏好表；由 [migration-20261111-user-config.md](migration-20261111-user-config.md) 于 2026-11-11 创建（当前 0 行）。`major_2nd` 已由 Dashboard 复验确认；`notice_version` 已由 [migration-20261111-notice-version.md](migration-20261111-notice-version.md) 于 2026-11-11 新增并复验。

| 列 | 类型 | NULL | 默认 | 说明 |
|---|---|---|---|---|
| `id` | `uuid` | NO | — | 主键；FK → `user.id`，`ON DELETE CASCADE` |
| `major_2nd` | `text` | YES | — | 第二主修名称，取值属于 `app/constant.MAJOR_2nd_list`；NULL = 尚未选择 |
| `notice_version` | `integer` | NO | `0` | 已确认的最高公告版本；0 = 未确认 |
| `updated_at` | `timestamptz` | NO | `now()` | 写入时间；无触发器自动刷新，应用不依赖 |

应用在登录后读取（`src/storage.fetch_user_config`），用户改选时 upsert（`save_major_2nd`），确认公告时 upsert `notice_version`（`save_notice_version`）；不预建行。公告内容来自 `data/announcements.json`，登录后一次性聚合未读版本，见 `src/announcements.py` / `app/notice.py`。

### `study_plan`（目录课程计划）

| 列 | 类型 | NULL | 默认 | 说明 |
|---|---|---|---|---|
| `id` | `uuid` | NO | — | PK 之一；FK → `user.id` |
| `course_id` | `text` | NO | — | PK 之一；规范化课程码（`_course_key`） |
| `study_period` | `text` | YES | — | `STUDY_CAMPUS` 键；允许 NULL（已选、未排学期） |
| `selected` | `boolean` | NO | `false` | 已选标记；2026-11-11 迁移存量行回填为 `true`，之后默认 `false` |
| `updated_at` | `timestamptz` | NO | `now()` | 最后写入时间 |

### `pe` / `college_ge` / `four_area_ge`（自由录入）

三表结构相同：

| 列 | 类型 | NULL | 默认 | 说明 |
|---|---|---|---|---|
| `id` | `uuid` | NO | — | PK 之一；FK → `user.id` |
| `course_id` | `text` | NO | — | PK 之一；用户手填 `CODE Title` 整格文本 |
| `study_period` | `text` | YES | — | 未填时存 NULL（草稿行） |
| `selected` | `boolean` | NO | `false` | 已选；取消勾选保留该行为草稿（`selected=false`） |
| `credits` | `integer` | NO | `0` | 用户手填学分 |
| `updated_at` | `timestamptz` | NO | `now()` | — |

### `english`（固定英文目录）

| 列 | 类型 | NULL | 默认 | 说明 |
|---|---|---|---|---|
| `id` | `uuid` | NO | — | PK 之一；**无 FK** |
| `course_id` | `text` | NO | — | PK 之一；规范化英文课程码（HK 码，含 ENG* 等价码） |
| `study_period` | `text` | YES | — | 空 = 已选未排（backlog）或历史遗留 |
| `selected` | `boolean` | NO | `false` | 已选；`study_period=NULL AND selected=true` 即 backlog |
| `credits` | `integer` | YES | — | 应用不使用（学分由目录推导） |

> 该表**没有** `updated_at` 列。

### `other_courses`（scheme 外课程）

| 列 | 类型 | NULL | 默认 | 说明 |
|---|---|---|---|---|
| `id` | `uuid` | NO | — | PK 之一；**无 FK** |
| `course_id` | `text` | NO | — | PK 之一；手填 `CODE Title` |
| `study_period` | `text` | YES | — | — |
| `selected` | `boolean` | NO | `false` | 已选；未勾选也可作为草稿保存 |
| `credits` | `integer` | NO | `0` | — |
| `updated_at` | `timestamptz` | NO | `now()` | — |

### `chinese`（遗留，勿使用）

`id uuid`、`course_id text`、`credits integer NULL`、`study_period text NULL`，当前 0 行。仓库没有指向该表的代码路径；中文课程写 `study_plan`。

### `study_plan_backup_20261024`

`id` / `updated_at` / `course_id` / `study_period` 的普通拷贝，无主键、无约束。仅作历史备份，应用不读写。

## 5. 关系与约束

- `id` 外键：`study_plan`、`pe`、`college_ge`、`four_area_ge` → `user.id`；`user_config.id` → `user.id`（`ON DELETE CASCADE`）。
- `english`、`other_courses` 的 `id` **没有**外键（历史原因）；清理账户时需手工处理。
- 六张计划表均以 `(id, course_id)` 唯一；`course_id` 的 canonical 化规则见 `docs/migration-20261024-equivalence-keys.md`，改动 CSV 映射时必须同步迁移存量 `study_plan`。

## 6. 已知不确定项（需 Dashboard 确认）

PostgREST OpenAPI 只暴露表/列/外键，以下内容无法从只读查询确认：

- **RLS**：各表是否启用 Row Level Security、策略是否按 `auth.uid()` 限制——需在 Dashboard → Authentication → Policies 查看。应用层的访问控制不能替代 RLS。
- **`updated_at` 触发器**：列默认值存在，但是否有 `BEFORE UPDATE` 触发器自动刷新需查 Dashboard → Database → Triggers。
- **`chinese` 与 `study_plan_backup_20261024`** 是否为历史残留、可否清理，需维护者确认后再动。

## 7. Schema 变更流程

1. 在本目录新增 `docs/migration-YYYYMMDD-<topic>.md` Runbook：背景、变更清单、预检 SQL、备份、事务内 DDL、复验 SQL、回滚、上线顺序、人工验证清单。
2. 只读查询当前结构（`information_schema.columns` / `pg_constraint`）确认假设；假设与线上不符时先查明原因。
3. 由维护者在 Supabase SQL Editor 执行；**先 SQL、后部署应用**（新代码若先上线会因缺列/约束不符而写入失败）。
4. 迁移完成后更新本文件的字段、NULL 约束、行数与「最后核验」日期。
