# 仓库指南

> 以中文撰写

## 项目概述

CUHK IDADM（2025 入学，沙田校区）学生的 Streamlit Web 应用，用于规划 4 年双校区（CUHK ↔ CUHKSZ）课程、跟踪毕业要求并强制执行学分上限。支持基于 Supabase 的登录和学习计划云保存。

**过时文档警告：** `CLAUDE.md` 和 `README.md` 描述的是旧版 756 行 `main.py` 单体文件，包含 `src/pdf_generator.py`、`src/word_generator.py`、`src/page_display.py` 和 `pip install -r requirements.txt`——这些文件均已不存在。仓库已重构（见 `plan/REFACTOR_PLAN.md`）；本文件反映当前实际状态。

## 架构与数据流

三层架构，显式依赖注入（无全局状态）：

```
main.py（轻量入口）→ app/（Streamlit UI）→ src/（数据 + 持久化）
```

- **main.py**（~60 行）：`load_cache_data()`（`@st.cache_data`）调用 `src/data_retrieval.load_all_data()`；页面配置；侧边栏登录；二专选择框；`try/except data.FileMissingError | data.DataFormatError → st.error + st.stop`；创建 4 个标签页——**仅 University Core（`app/ucore.ui`）已接入；其余三个标签页为空壳**。
- **数据在运行时加载，而非导入时**：`load_all_data()` 读取 `data/*.csv|json` 并返回不可变的 `CourseDataContext`（frozen `@dataclass`），包含 `course_info`、`equivalence_courses`、`equivalence_bidicts`、`course_list`、`major_2_requirement`。
- **上下文透传**：`CourseDataContext` 通过 UI 函数显式传递（`ucore.ui(context)`），并传入每个 getter（`get_course_info(context, ...)`）。永远不在模块级导入数据。
- **Session state**：仅 `login_status` 和 `user_id`（在 `app/login.py` 中设置）。游客 `user_id` → 学习期编辑无操作，`show_course_info` 返回空白。
- **编辑流程**：`st.data_editor(on_change=func)` → `src/storage.data_on_change(key, df)` 读取 `st.session_state[key]` 中已编辑/新增/删除的行 → 在 Supabase `study_plan` 表上执行 `upsert_data` / `delete_data`，键为 `(id, course_id)`，冲突策略 `on_conflict='id,course_id'`。
- **校区轮换**：`STUDY_CAMPUS` 字典（学期标签 → `'CUHK'`/`'CUHKSZ'`）单一来源定义在 `app/constant.py`。课程 ID 的校区判断：`determine_campus()` —— 第 4 个字符为字母 → CUHK（`hk`），否则 → CUHKSZ（`sz`）。

## 关键目录

| 路径 | 用途 |
|---|---|
| `app/` | Streamlit UI 包：`ucore.py`（University Core 标签页）、`login.py`（认证表单）、`components.py`（共享组件）、`constant.py`（专业列表、校区映射） |
| `src/` | 非 UI 层：`data_retrieval.py`（CSV/JSON 加载 + getter）、`storage.py`（Supabase 持久化）、`auth.py`（Supabase 用户认证） |
| `data/` | 静态目录：`course_list.csv`（课程目录）、`course_list.json`（按专业分组）、`equivalence_courses.csv`（HK↔SZ 映射）、`2nd_major_credit_requirement.json` |
| `tests/` | pytest 测试（仅 `test_data_retrieval.py`） |
| `docs/` | `user_guide.md`、课程键设计文档（待完成）、`assets/` 截图 |
| `plan/` | 重构/Schema/功能规划文档——大型变更前请阅读 |
| `.github/workflows/` | CI（`test.yml`） |

## 开发命令

```bash
uv sync                # 安装依赖（uv 管理；Python 3.14 由 .python-version 指定）
uv run streamlit run main.py   # 运行应用
pytest tests/ -v       # 运行测试（必须从仓库根目录运行——测试使用相对 data/ 路径）
```

无构建步骤，无 lint/format 配置，`pyproject.toml` 中无 `[tool.*]` 部分。

## 代码规范与常见模式

- **命名**：函数/参数用 `snake_case`，模块常量用 `ALL_CAPS`（`MAJOR_LIST`、`STUDY_CAMPUS`），类/异常用 `CamelCase`。注意现有风格使用非 PEP8 注解间距 `name : Type`——请匹配周围代码。
- **类型**：处处显式注解；校区用 `Literal['hk', 'sz']`；不可变上下文对象用 frozen `@dataclass`。
- **错误处理**：按模块的异常层级——`DataLoadError` 基类下有 `FileMissingError`、`DataFormatError`、`InfoMissingError`（`src/data_retrieval.py`）；`AuthServiceError`（`src/auth.py`）。应用捕获数据层错误并映射为 `st.error` + `st.stop()`。
- **依赖注入**：函数以 `context: CourseDataContext` 为第一参数；无模块级数据全局变量。
- **异步**：无——全程同步代码。保持这种方式（Streamlit 重运行模型）。
- **Streamlit 模式**：`@st.cache_data` 用于昂贵加载；`st.session_state` 仅用于登录；`st.data_editor` 带 `on_change` 回调；`st.dialog` 用于注册；`st.rerun` 用于变更后刷新。
- **存储访问**：`src/storage.py` 从 `st.secrets['SUPABASE_URL'|'SUPABASE_KEY']` 构建模块级 Supabase 客户端——密钥缺失时会崩溃；新代码路径中应优雅处理。

## 重要文件

| 文件 | 重要性 |
|---|---|
| `main.py` | 入口点——组合根 |
| `pyproject.toml` / `uv.lock` / `.python-version` | 工具链：uv、Python 3.14 |
| `src/data_retrieval.py` | 所有目录数据访问；`CourseDataContext`、`load_all_data()`、getter、`convert_course_id()`（bidict） |
| `src/storage.py` | 学习计划的 Supabase 读取/插入/删除 |
| `src/auth.py` | 注册/登录、密码强度验证 |
| `app/constant.py` | `MAJOR_LIST`、`MAJOR_2nd_list`、`STUDY_CAMPUS`——唯一事实来源 |
| `app/components.py` | `table_editor()` 组件包装器、`study_period_col_config` |
| `data/*` | 主目录——视为只读输入 |
| `.streamlit/secrets.toml` | Supabase 密钥（已 gitignore） |

## 运行时/工具链偏好

- **包管理器**：`uv`——`uv.lock` 为权威来源。不要按 README/CI 添加 `requirements.txt` 或 `pip install`；优先使用 `uv add` / `uv sync`。
- **运行时**：Python `>=3.14`（`.python-version` 锁定 3.14）。Streamlit `>=1.58.0`、`supabase>=2.31.0`、`bidict>=0.23.1`、`pytest>=9.1.1`（声明为运行时依赖——奇怪但已存在）。
- **CI 不一致**：`.github/workflows/test.yml` 使用 Python 3.12 + `pip install -r requirements.txt`（不存在）——CI 当前损坏且与 uv/Python 3.14 不一致。修复它是合理的。
- **许可证**：MIT。

## 测试与质量保证

- **框架**：pytest，无配置文件（`pytest.ini`/`[tool.pytest]` 不存在），无 `conftest.py`，无覆盖率工具/阈值。
- **运行**：从仓库根目录 `pytest tests/ -v`（需要相对 `data/` 路径）。
- **覆盖率**：`tests/test_data_retrieval.py`——26 个测试，4 个类（`TestDetermineCampus`、`TestDataLoading`、`TestGetters`、`TestConvertCourseId`），每个类有类级 `context` fixture 调用 `load_all_data()`。
- **缺口**：仅 `src/data_retrieval.py` 有测试。`src/storage.py`、`src/auth.py`、`app/*`、`main.py`、错误路径处理（`FileMissingError`/`DataFormatError`）和学分上限规则零测试。添加覆盖率时请遵循现有 fixture 模式（每个类 `context = load_all_data()`）。
- **编辑时已知风险**：`app/ucore.py` 会修改共享的 `study_period_col_config` 字典（泄漏到后续编辑器）；`src/auth.py` 比较明文密码；`show_course_info` 每次重运行都无缓存地访问 Supabase；`data_retrieval.py` 中有两个不带 `from` 的裸 `raise InfoMissingError`。
