# 一键启动脚本 Decision Architecture

## Executive Summary

本架构文档定义了量化交易平台一键启动脚本的技术实施方案，采用纯Python + CLI的跨平台部署自动化架构。该方案通过智能环境检测、依赖管理和服务编排，实现非技术用户在10分钟内完成完整平台部署的目标，同时确保90%以上常见环境问题的自动解决能力。

## Project Initialization

本项目不需要特定的启动器模板，采用原生Python开发。开发团队可以直接创建项目结构：

```bash
mkdir one-click-launcher
cd one-click-launcher
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install psutil rich requests
```

## Decision Summary

| Category | Decision | Version | Affects Epics | Rationale |
| -------- | -------- | ------- | ------------- | --------- |
| 核心引擎 | Python 3.11 | 3.11.14+ | Epic 1, 2, 3 | 最稳定的LTS版本，跨平台兼容性最佳 |
| 系统监控 | psutil | 7.1.3+ | Epic 1, 3 | 跨平台进程和系统资源监控标准库 |
| CLI界面 | rich | 13.9.4+ | Epic 3 | 美观的命令行界面，进度条和表格支持 |
| 配置管理 | configparser | 内置 | Epic 1, 2 | Python内置，无额外依赖，可靠稳定 |
| 日志系统 | logging | 内置 | Epic 3 | Python内置，结构化日志支持 |
| HTTP请求 | requests | 2.32.3+ | Epic 1 | 简洁可靠的HTTP客户端库 |
| 进程管理 | subprocess | 内置 | Epic 2 | Python内置，跨平台进程管理 |
| 端口分配 | Redis:6379, Backend:8000, Frontend:3000 | - | Epic 2 | 基于现有项目配置，避免端口冲突 |

## Project Structure

```
one-click-launcher/
├── launcher.py                 # 主启动入口点
├── requirements.txt           # Python依赖清单
├── README.md                  # 用户使用指南
├── LICENSE                    # 开源许可证
├── config/
│   ├── config.ini             # 默认配置文件
│   └── platform-configs/      # 平台特定配置目录
│       ├── windows.ini        # Windows平台配置
│       ├── macos.ini          # macOS平台配置
│       └── linux.ini          # Linux平台配置
├── core/                      # 核心功能模块
│   ├── __init__.py
│   ├── environment_detector.py # 环境检测模块
│   ├── dependency_installer.py # 依赖安装模块
│   ├── service_manager.py     # 服务管理模块
│   ├── progress_tracker.py    # 进度跟踪模块
│   └── error_handler.py       # 错误处理模块
├── services/                  # 服务管理模块
│   ├── __init__.py
│   ├── database_service.py    # 数据库服务管理
│   ├── backend_service.py     # 后端服务管理
│   └── frontend_service.py    # 前端服务管理
├── utils/                     # 工具模块
│   ├── __init__.py
│   ├── logger.py              # 日志工具
│   ├── file_utils.py          # 文件操作工具
│   └── network_utils.py       # 网络检测工具
├── assets/                    # 资源文件
│   ├── offline_packages/      # 离线依赖包存储
│   └── templates/             # 配置模板文件
├── tests/                     # 测试文件
│   ├── test_environment_detector.py
│   ├── test_service_manager.py
│   └── test_integration.py
├── scripts/                   # 辅助脚本
│   ├── build.py               # 打包脚本
│   ├── install.bat            # Windows安装脚本
│   └── install.sh             # Unix安装脚本
└── docs/                      # 文档目录
    ├── user_guide.md          # 用户指南
    └── technical_guide.md     # 技术指南
```

## Epic to Architecture Mapping

| Epic | 负责模块 | 主要职责 | 关键文件 |
| ---- | -------- | -------- | -------- |
| Epic 1: 环境检测与自动配置引擎 | core/environment_detector.py, core/dependency_installer.py, utils/ | 检测系统环境、安装依赖、配置基础设置 | environment_detector.py, dependency_installer.py, network_utils.py |
| Epic 2: 服务编排与启动管理 | core/service_manager.py, services/ | 按顺序启动服务、监控服务状态、管理服务生命周期 | service_manager.py, database_service.py, backend_service.py, frontend_service.py |
| Epic 3: 错误处理与用户支持 | core/error_handler.py, core/progress_tracker.py, utils/logger.py | 错误检测、用户友好提示、进度跟踪、日志记录 | error_handler.py, progress_tracker.py, logger.py |

## Technology Stack Details

### Core Technologies

**Python 3.11.14+ (LTS)**
- 选择理由：最稳定的长期支持版本，跨平台兼容性最佳
- 优势：丰富的第三方库生态，成熟的并发和异步支持
- 验证日期：2025-11-04

**psutil 7.1.3+**
- 功能：跨平台系统监控和进程管理
- 用途：检测端口占用、监控服务状态、获取系统信息
- 验证状态：活跃维护，跨平台兼容性良好

**rich 13.9.4+**
- 功能：美观的命令行界面和进度指示
- 用途：用户体验优化，进度条和表格显示
- 特色：支持彩色输出、进度条、表格、语法高亮

**requests 2.32.3+**
- 功能：HTTP客户端库
- 用途：网络连接检测、在线资源下载
- 优势：简洁API，成熟的错误处理机制

### Integration Points

**服务启动序列集成：**
1. Redis启动 (端口6379) → 等待就绪 (30秒超时)
2. 后端API启动 (端口8000) → 健康检查通过 (60秒超时)
3. 前端应用启动 (端口3000) → 构建完成 (120秒超时)

**配置管理集成：**
- 平台特定配置覆盖默认配置
- 环境变量优先级高于配置文件
- 运行时配置热更新支持

**错误处理集成：**
- 统一异常格式：{code, message, solution, details}
- 分级错误处理：WARNING(继续)、ERROR(重试)、FATAL(终止)
- 自动恢复机制：网络重试、端口清理、服务重启

## Implementation Patterns

这些模式确保所有AI代理实现的一致性：

**启动流程模式：**
```python
async def start_service(service_name: str) -> bool:
    try:
        # 1. 检测依赖
        await check_dependencies(service_name)
        # 2. 启动服务
        process = await launch_service(service_name)
        # 3. 等待就绪
        await wait_for_ready(service_name, timeout=60)
        # 4. 健康检查
        return await health_check(service_name)
    except ServiceError as e:
        await handle_service_error(service_name, e)
        return False
```

**错误处理模式：**
```python
try:
    # 操作代码
    result = await perform_operation()
except NetworkError as e:
    log_error(f"网络错误: {e}")
    return await retry_with_backoff(operation)
except PermissionError as e:
    log_error(f"权限错误: {e}")
    return await suggest_admin_privileges()
except Exception as e:
    log_error(f"未知错误: {e}")
    return await handle_unknown_error(e)
```

**配置读取模式：**
```python
def load_config(platform: str) -> Config:
    # 1. 加载默认配置
    config = load_default_config()
    # 2. 加载平台特定配置
    platform_config = load_platform_config(platform)
    # 3. 合并配置
    config.update(platform_config)
    # 4. 应用环境变量覆盖
    config.update_from_env()
    return config
```

## Consistency Rules

### Naming Conventions

**文件命名：** snake_case
- environment_detector.py
- service_manager.py
- dependency_installer.py

**类命名：** PascalCase
- EnvironmentDetector
- ServiceManager
- DependencyInstaller

**函数命名：** snake_case
- detect_python_version()
- start_service()
- install_dependencies()

**常量命名：** UPPER_SNAKE_CASE
- MIN_PYTHON_VERSION
- DEFAULT_TIMEOUT
- MAX_RETRY_COUNT

**配置键：** kebab-case
- min-python-version
- default-timeout
- max-retry-count

### Code Organization

**目录结构模式：**
- core/ - 核心业务逻辑
- services/ - 服务管理模块
- utils/ - 通用工具函数
- config/ - 配置文件管理
- tests/ - 测试文件

**导入顺序模式：**
1. 标准库导入
2. 第三方库导入
3. 本地模块导入
4. 相对导入

**异常处理模式：**
- 总是使用具体的异常类型
- 提供有意义的错误消息
- 记录详细的错误信息
- 提供恢复建议

### Error Handling

**统一异常格式：**
```python
class LauncherError(Exception):
    def __init__(self, code: str, message: str, solution: str, details: str = None):
        self.code = code
        self.message = message
        self.solution = solution
        self.details = details
        super().__init__(f"[{code}] {message}")
```

**错误分类：**
- WARNING: 可继续执行的问题
- ERROR: 可重试的失败
- FATAL: 必须终止的严重错误

**用户友好错误消息：**
- 避免技术术语
- 提供具体解决步骤
- 包含相关文档链接
- 支持多语言（可选）

### Logging Strategy

**日志格式：**
```
[2025-11-04 15:30:00] [INFO] [EnvironmentDetector] 检测到Python 3.11.14
[2025-11-04 15:30:01] [WARNING] [DependencyInstaller] Node.js未安装，开始自动安装
[2025-11-04 15:30:15] [ERROR] [ServiceManager] 端口8000被占用，尝试清理
```

**日志级别：**
- DEBUG: 详细的调试信息（开发阶段）
- INFO: 一般信息记录（用户操作）
- WARNING: 警告信息（可继续执行）
- ERROR: 错误信息（需要处理）

**日志轮转：**
- 最大文件大小：10MB
- 保留文件数量：5个
- 压缩旧日志文件

## Data Architecture

**配置数据模型：**
```python
@dataclass
class ServiceConfig:
    name: str
    port: int
    host: str = "localhost"
    startup_command: str = ""
    health_check_url: str = ""
    timeout: int = 60
    dependencies: List[str] = field(default_factory=list)
```

**服务状态模型：**
```python
@dataclass
class ServiceStatus:
    name: str
    status: str  # "starting", "running", "stopped", "error"
    pid: Optional[int] = None
    port: Optional[int] = None
    last_check: Optional[datetime] = None
    error_message: Optional[str] = None
```

**进度跟踪模型：**
```python
@dataclass
class ProgressInfo:
    current_step: int
    total_steps: int
    step_name: str
    step_description: str
    percentage: float
    estimated_remaining: Optional[int] = None
```

## API Contracts

**健康检查API：**
```
GET /health
Response: {"status": "healthy", "timestamp": "2025-11-04T15:30:00Z"}
```

**服务状态API：**
```
GET /api/services/status
Response: {
  "redis": {"status": "running", "port": 6379},
  "backend": {"status": "running", "port": 8000},
  "frontend": {"status": "running", "port": 3000}
}
```

**错误响应格式：**
```
{
  "status": "error",
  "error": {
    "code": "PORT_OCCUPIED",
    "message": "端口8000被其他程序占用",
    "solution": "请关闭占用端口的程序或修改配置文件中的端口号",
    "details": "Process 'nginx' is using port 8000"
  },
  "timestamp": "2025-11-04T15:30:00Z"
}
```

## Security Architecture

**权限管理：**
- 检测管理员权限需求
- 提供权限申请指导
- 支持UAC提升（Windows）

**网络安全：**
- 仅本地服务启动（localhost绑定）
- 不开放外部端口访问
- 安全的临时文件处理

**输入验证：**
- 配置文件格式验证
- 端口范围检查（1024-65535）
- 路径遍历攻击防护

**进程隔离：**
- 服务进程独立运行
- 避免权限提升攻击
- 安全的进程通信机制

## Performance Considerations

**启动时间优化：**
- 并行依赖检查
- 智能缓存机制
- 预下载常用依赖包

**资源使用优化：**
- 异步操作避免阻塞
- 内存使用监控
- CPU使用率控制

**网络优化：**
- 离线安装包支持
- 断点续传下载
- 镜像源自动切换

**用户体验优化：**
- 实时进度显示
- 剩余时间估算
- 操作取消支持

## Deployment Architecture

**打包策略：**
- PyInstaller生成独立可执行文件
- 支持多平台打包（Windows/macOS/Linux）
- 内置依赖包减少网络依赖

**分发策略：**
- GitHub Releases发布
- 自动更新机制
- 版本回滚支持

**安装策略：**
- 零依赖安装包
- 智能路径选择
- 桌面快捷方式创建

## Development Environment

### Prerequisites

**开发环境要求：**
- Python 3.11+ (开发环境)
- Git 2.30+ (版本控制)
- VS Code / PyCharm (推荐IDE)

**测试环境要求：**
- 多平台虚拟机（Windows 10/11, macOS 10.15+, Ubuntu 18.04+）
- Docker (容器化测试)
- 网络模拟工具

### Setup Commands

```bash
# 1. 克隆项目
git clone <repository-url>
cd one-click-launcher

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发依赖

# 4. 运行测试
python -m pytest tests/

# 5. 本地开发
python launcher.py --debug

# 6. 构建发布包
python scripts/build.py --platform all
```

**开发工具配置：**
```bash
# 代码格式化
black . --line-length 88
isort .

# 类型检查
mypy core/ services/ utils/

# 代码质量检查
flake8 core/ services/ utils/
pylint core/ services/ utils/

# 安全检查
bandit -r core/ services/ utils/
```

## Architecture Decision Records (ADRs)

### ADR-001: 选择Python作为核心引擎
**状态：已接受**
**日期：2025-11-04**
**决策：采用Python 3.11作为一键启动脚本的核心引擎**
**理由：**
- 跨平台兼容性最佳，在Windows/macOS/Linux上表现一致
- 丰富的系统管理库生态（psutil, subprocess等）
- 成熟的异常处理和错误恢复机制
- 简单的打包和分发（PyInstaller）
**替代方案考虑：** Node.js, Go, Rust
**后果：** 接受Python的相对性能劣势，换取开发效率和跨平台兼容性

### ADR-002: 采用CLI界面而非GUI
**状态：已接受**
**日期：2025-11-04**
**决策：使用命令行界面而非图形用户界面**
**理由：**
- 符合"无聊技术"原则，确保最大可靠性
- 避免GUI框架的复杂性和跨平台问题
- 更好的自动化和脚本集成能力
- 减少依赖和打包体积
**替代方案考虑：** Electron, Tauri, Tkinter
**后果：** 用户体验相对简单，但确保了功能实现的可靠性

### ADR-003: 三层服务启动架构
**状态：已接受**
**日期：2025-11-04**
**决策：采用Redis→Backend→Frontend的三层服务启动架构**
**理由：**
- Redis作为缓存层，提供数据持久化支持
- 后端API提供业务逻辑和数据接口
- 前端应用提供用户界面
- 明确的依赖关系，避免启动冲突
**替代方案考虑：** 单体应用，微服务架构
**后果：** 增加了系统复杂性，但提供了更好的可维护性和扩展性

### ADR-004: 统一错误处理和用户友好消息
**状态：已接受**
**日期：2025-11-04**
**决策：实现统一的错误处理机制和用户友好的错误消息**
**理由：**
- 非技术用户需要清晰的问题描述和解决方案
- 统一的错误格式便于日志分析和问题诊断
- 自动恢复机制提高启动成功率
**替代方案考虑：** 技术性错误消息，静默失败
**后果：** 增加了开发复杂度，但显著改善了用户体验

### ADR-005: 离线优先的依赖管理策略
**状态：已接受**
**日期：2025-11-04**
**决策：优先使用离线依赖包，网络下载作为备选方案**
**理由：**
- 确保在网络受限环境下的可用性
- 减少外部依赖，提高启动成功率
- 提供更可预测的安装体验
**替代方案考虑：** 纯在线安装，混合模式
**后果：** 增加了分发包大小，但确保了在各种网络环境下的可靠性

---

**架构验证状态：** ✅ 所有决策已验证，相互兼容，覆盖所有PRD需求

**实施就绪状态：** ✅ 架构文档完整，可指导AI代理进行一致实现

**下一步行动：** 开始Phase 4实施阶段，使用create-story工作流生成具体的用户故事实施计划

---

_Generated by BMAD Decision Architecture Workflow v1.3.2_
_Date: 2025-11-04_
_For: aTenderLion_