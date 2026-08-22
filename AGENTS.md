# 仓库指南

> 以中文撰写

## 项目概述

CUHK IDADM（2025 入学，沙田校区）学生的 Streamlit Web 应用，用于规划 4 年双校区（CUHK ↔ CUHKSZ）课程、跟踪毕业要求并强制执行学分上限。支持基于 Supabase 的登录、学习计划云保存与 PDF/Word 导出，可 Docker 部署。

## 架构与数据流

三层架构，显式依赖注入（无模块级数据全局变量）：

```
main.py（轻量入口）→ app/（Streamlit UI）→ src/（数据 + 持久化 + 导出）
```

- **main.py**（~80 行）：`load_cache_data()`（`@st.cache_data`）调用 `src.data_retrieval.load_all_data()`；页面配置；侧边栏登录；二专选择框（仅当已选二专才渲染 4 个标签页）；`try/except data.FileMissingError | data.DataFormatError → st.error + st.stop`；4 个标签页全部接入：University Core（`app/ucore.ui`）、Interdisciplinary Data Analytics（`app/ida.ui`）、2nd Major（`app/major_2.ui`）、Planner（`app/planner.ui`）。
- **数据在运行时加载，而非导入时**：`load_all_data()` 读取 `data/*.csv|json` 并返回不可变的 `CourseDataContext`（frozen `@dataclass`），包含 `course_info`、`equivalence_courses`、`equivalence_bidicts`、`course_list`、`major_2_requirement`。
- **上下文透传**：`CourseDataContext` 通过 UI 函数显式传递（`ucore.ui(context, ...)`），并传入每个 getter（`get_course_info(context, ...)`）。
- **Session state**：`login_status` 与 `user_id`（`app/login.py`）；各 `data_editor` 的 widget key（`ucore-*`、`ida-*`、`major2-*`）；`guest_notice_shown`；`main-tabs`（保持活动标签页）。游客 `user_id` → 学习期编辑不持久化，`show_course_info` 返回空白。
- **编辑流程（目录表）**：`ucore` 的 Required Courses 与 Chinese Language、`ida`、`major_2` 标签页的目录表（课程来自 `data/major_course_list.json`）通过 `app/components.table_editor()`（`st.data_editor(on_change=...)`）渲染，`on_change` 指向 `src/storage.data_on_change(key, df)`。该函数读取 `st.session_state[key]` 中的 `edited_rows`/`added_rows`/`deleted_rows`，在 Supabase `study_plan` 表上 `upsert_data`/`delete_data`，键为 `(id, course_id)`、冲突策略 `on_conflict='id,course_id'`。课程身份 = DataFrame 的 index label（经 `_course_key()` 规整为 HK 等价码），而非可编辑的显示列——因此改显示文字无法劫持 `course_id`。游客（`user_id` 缺失）直接跳过写入；index 非字符串时 `st.error` 并中止，防止 RangeIndex 行号冒充课程键。
- **用户录入表（无目录）**：University Core 下的 PE、College GE、Four Area of GE 为自由录入表（`app/ucore._user_input_section`），各自写入独立 Supabase 表 `pe`/`college_ge`/`four_area_ge`（`pe_on_change`/`college_ge_on_change`/`four_area_on_change` 均为 `user_input_on_change` 的封装）。此时课程身份 = 用户手填的 `CUHK`/`CUHKSZ` 单元格（非 index）；空 `study_period` 存为 `NULL`，单条失败不影响其余行。各表通过独立表名相互隔离，召回互不冲突。Chinese Language 是目录表而非录入表：课程清单来自 `major_course_list.json["University Core"]["Chinese Language"]`，经 `app/ucore._catalogue_section` 渲染、`data_on_change` 写入 `study_plan`。
- **数据召回与展示**：`src/storage.fetch_data(user_id, table_name)` 单表读取，`fetch_all_planned(user_id)` 汇总全部 5 张表并打 `source` 标签；Planner 标签页据此集中计算。
- **IDA 与 2nd Major 的课表来源**：IDA 标签页的必修分段（Faculty Package/Required Courses/COOP）与等价转换使用 `Interdisciplinary Data Analytics` 专业；但其选修 Group A/B 的**课程清单**取自用户所选 2nd major 的 `1st Major Elective Courses`（复刻重构前的生产行为）。2nd Major 标签页的 "Elective Courses" UI 对应数据键 `2nd Major Elective Courses`，等价转换使用所选 2nd major。
- **Planner 标签页（只读聚合）**：`app/planner.ui` 不写入，仅经 `fetch_all_planned` 拉取全部计划后即时计算。学分上限由 `_check_credit_limit` 强制执行——常规学期 9–18（Year 1 上限 19）、暑期 0–6、整学年 18–39，越界 `st.error` 提示需申请；毕业要求（`app/constant.GRADUATION_REQUIREMENT`）逐项比对（含 3000+/4000+ 层级学分），支持 PDF（`src/pdf_generator`）/Word（`src/word_generator`）导出（按学年/学期分页的总学分表）。游客访问时显示提示并直接返回，强制登录后才可用。
- **校区轮换**：`STUDY_CAMPUS` 字典（学期标签 → `'CUHK'`/`'CUHKSZ'`）单一来源定义在 `app/constant.py`。课程 ID 的校区判断：`determine_campus()` —— 长度需 ≥ 7，第 4 个字符（index 3）为字母 → CUHK（`hk`），否则 → CUHKSZ（`sz`），其余抛 `DataLoadError`；`determine_level()` 据校区提取课程层级（1–4）用于选修层级学分统计。
- **认证**：`src/auth.py` 使用 PBKDF2-HMAC-SHA256（stdlib）哈希密码，登入本地验证（密码不作为查询条件）；存量明文密码行登入成功后原地升级为哈希。

## 关键目录

| 路径 | 用途 |
|---|---|
| `app/` | Streamlit UI 包：`ucore.py`（University Core：目录表 + PE/College GE/Four Area GE 录入表）、`ida.py`（IDA 1st Major：Faculty Package/Required/COOP/选修 A·B）、`major_2.py`（2nd Major：Required/Research/Elective）、`planner.py`（只读聚合 + 学分上限 + 导出）、`login.py`（登录/注册表单与游客状态清理）、`components.py`（`table_editor()` 封装、`study_period_col_config`）、`constant.py`（专业列表、校区映射、毕业要求） |
| `src/` | 非 UI 层：`data_retrieval.py`（CSV/JSON 加载 + getter + 等价转换）、`storage.py`（Supabase 持久化，5 张表 `study_plan`/`pe`/`college_ge`/`four_area_ge`/`english`）、`auth.py`（Supabase 用户认证）、`pdf_generator.py` / `word_generator.py`（Planner 的导出功能） |
| `data/` | 静态目录（视为只读输入）：`course_list.csv`（课程目录）、`major_course_list.json`（按专业分组）、`equivalence_courses.csv`（HK↔SZ 映射）、`2nd_major_credit_requirement.json` |
| `tests/` | pytest 测试：`test_data_retrieval.py`、`test_auth.py`、`conftest.py`（stub supabase、隔离 session_state） |
| `docs/` | `user_guide.md`、`assets/` 截图 |
| `.github/workflows/` | CI（`test.yml`，uv + Python 3.14） |

## 开发命令

```bash
uv sync                          # 安装依赖（uv 管理；.python-version 锁定 3.14）
uv run streamlit run main.py     # 运行应用
uv run pytest tests/ -v          # 运行测试（61 个，全部离线——conftest stub 了 supabase）
docker compose up -d --build     # 容器部署（需要 .streamlit/secrets.toml）
```

本地运行需要 `.streamlit/secrets.toml`（`SUPABASE_URL` / `SUPABASE_KEY`，已 gitignore）。无构建步骤；无 lint/format 配置。

## 代码规范与常见模式

- **命名**：函数/参数用 `snake_case`，模块常量用 `ALL_CAPS`（`MAJOR_LIST`、`STUDY_CAMPUS`），类/异常用 `CamelCase`。注意现有风格使用非 PEP8 注解间距 `name : Type`——请匹配周围代码。
- **类型**：处处显式注解；校区用 `Literal['hk', 'sz']`；不可变上下文对象用 frozen `@dataclass`。
- **错误处理**：按模块的异常层级——`DataLoadError` 基类下有 `FileMissingError`、`DataFormatError`、`InfoMissingError`（`src/data_retrieval.py`）；`AuthServiceError`（`src/auth.py`）。应用捕获数据层错误并映射为 `st.error` + `st.stop()`。
- **依赖注入**：函数以 `context: CourseDataContext` 为第一参数；无模块级数据全局变量。
- **异步**：无——全程同步代码。保持这种方式（Streamlit 重运行模型）。
- **Streamlit 模式**：`@st.cache_data` 用于昂贵加载；`st.data_editor` 带 `on_change` 回调；`st.dialog` 用于注册；`st.rerun` 用于变更后刷新。`session_state` 不止用于登录（见上）。
- **存储访问**：`src/storage.py` 从 `st.secrets['SUPABASE_URL'|'SUPABASE_KEY']` 构建模块级 Supabase client——密钥缺失时 import 即崩溃；新代码路径应优雅处理。
- **密码安全**：密码一律经 `src/auth.hash_password()` 存储；登入用 `verify_password()` 本地验证；禁止以明文密码作为查询条件。哈希细节：PBKDF2-HMAC-SHA256，迭代 600,000（OWASP 建议），存储格式 `pbkdf2_sha256$<iterations>$<salt_hex>$<digest_hex>`（带方案前缀，便于日后迁移至 argon2/bcrypt）；`verify_password` 用 `hmac.compare_digest` 做常量时间比对，对畸形/明文一律返回 `False`。存量明文密码行登入成功后原地升级为哈希（升级失败非致命，下次成功登录重试）。密码强度 `validate_password_strength` 要求：≥8 字符且同时含大写、小写、数字（注意：登录框 placeholder 文案只提大小写，实际还强制数字——属文案与实现不一致，改动时留意）。

## 重要文件

| 文件 | 重要性 |
|---|---|
| `main.py` | 入口点——组合根 |
| `pyproject.toml` / `uv.lock` / `.python-version` | 工具链：uv、Python 3.14 |
| `src/data_retrieval.py` | 所有目录数据访问；`CourseDataContext`、`load_all_data()`、getter、`convert_course_id()`（bidict） |
| `src/storage.py` | 学习计划 Supabase 持久化：5 张表 `study_plan`/`pe`/`college_ge`/`four_area_ge`/`english`，`fetch_data`/`upsert_data`/`delete_data`/`fetch_all_planned` 与各 `on_change` 回调 |
| `src/auth.py` | 注册/登录、PBKDF2 密码哈希、密码强度验证 |
| `app/constant.py` | `MAJOR_LIST`、`MAJOR_2nd_list`、`STUDY_CAMPUS`、`GRADUATION_REQUIREMENT`——唯一事实来源 |
| `app/components.py` | `table_editor()` 组件包装器、`study_period_col_config` |
| `data/*` | 主目录——视为只读输入 |
| `.streamlit/secrets.toml` | Supabase 密钥（已 gitignore） |

## 运行时/工具链偏好

- **包管理器**：`uv`——`uv.lock` 为权威来源。不要添加 `requirements.txt` 或 `pip install`；优先使用 `uv add` / `uv sync`。
- **运行时**：Python `>=3.14`（`.python-version` 锁定 3.14）。运行时依赖（`[project].dependencies`）：`streamlit>=1.58.0`、`supabase>=2.31.0`、`bidict>=0.23.1`、`fpdf2>=2.7.9`（PDF 导出）、`python-docx>=1.1.0`（Word 导出）；pytest 在 dev dependency group（`[dependency-groups]`）。
- **CI**：`.github/workflows/test.yml` 使用 `astral-sh/setup-uv` + `uv sync --frozen` + `uv run pytest tests/ -v`，Python 3.14。
- **部署**：`Dockerfile` + `docker-compose.yml`（Supabase 密钥以 volume 挂载，不進鏡像）。
- **许可证**：MIT。

## 测试与质量保证

- **框架**：pytest，无配置文件（无 `pytest.ini`/`[tool.pytest]`）。`tests/conftest.py` 在收集前 stub `supabase` 模块并绑定 `st.secrets`，使全部测试离线可跑；autouse fixture 为每个测试提供隔离的 `st.session_state`。
- **运行**：`uv run pytest tests/ -v`（61 个测试，全部通过）。
- **覆盖**：`test_data_retrieval.py`（46 个）覆盖 `src/data_retrieval.py` 与 `src/storage.py` 的纯函数、数据完整性、课程键与持久化契约；`test_auth.py`（15 个）覆盖哈希/验证/登入/明文升级路径（假 client，无网络）。
- **缺口**：`app/*`、`main.py`、`src/pdf_generator.py`、`src/word_generator.py`、学分上限规则零测试；`FileMissingError`/`DataFormatError` 错误路径未测。添加覆盖率时遵循现有 fixture 模式（类级 `context = load_all_data()` 或 monkeypatch 假 client）。
