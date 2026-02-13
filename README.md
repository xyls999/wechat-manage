# 智慧表格助手 - FastAPI后端

## 📖 项目简介

基于FastAPI构建的Excel文件处理系统，主要功能：
- 用户认证（注册/登录/JWT）
- Excel文件上传
- 按会计月自动汇总数据
- 文件下载和预览
- 历史记录管理
- 内嵌后台管理页面（用户管理/文件管理/清理任务）
- 定时清理（默认清理3天前源文件与处理后文件）

## 🧭 管理后台入口

- 访问根路径：`http://localhost:8000/`（返回后台页面）
- 系统信息：`GET /api/v1/system/info`
- 管理接口前缀：`/api/v1/admin/*`

## 🚀 本地开发

### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env` 文件并修改配置：
```bash
DATABASE_URL=sqlite+aiosqlite:///./app.db
SECRET_KEY=your-secret-key-change-in-production-min-32-characters-long
UPLOAD_DIR=./uploads
ADMIN_AUTH_ENABLED=false
ADMIN_ALLOWED_ORIGINS=["*"]
CLEANUP_RETENTION_DAYS=3
CLEANUP_SCHEDULE_HOUR=3
CLEANUP_SCHEDULE_MINUTE=0
AI_API_KEY=
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini
AI_TIMEOUT_SECONDS=60
```

### 2.1 数据库迁移（Alembic）

```bash
# 初始化/升级数据库结构
alembic upgrade head
```

### 3. 运行服务

```bash
python main.py
```

服务将在 `http://localhost:8000` 启动

### 4. 测试功能

```bash
# 创建测试Excel文件
python create_test_excel.py

# 运行API测试
python test_api.py
```

## 📚 API文档

启动服务后访问：
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🌐 Render部署

### 方式1: 通过GitHub自动部署（推荐）

1. 将代码推送到GitHub仓库
2. 登录 [Render](https://render.com)
3. 创建新的Web Service
4. 连接GitHub仓库
5. Render会自动检测 `render.yaml` 配置
6. 设置环境变量：
   - `SECRET_KEY`: 生成一个32位以上的随机字符串
   - `DATABASE_URL`: 使用Render提供的PostgreSQL（可选）或保持SQLite
7. 点击部署

### 方式2: 手动配置

1. 登录Render
2. 创建新的Web Service
3. 配置如下：
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Environment**: Python 3
4. 添加环境变量
5. 部署

### 需要上传的文件

部署到Render只需要以下文件（不需要整个虚拟环境）：

```
fastapi/
├── app/                  # 应用代码
│   ├── api/
│   ├── core/
│   ├── models/
│   ├── schemas/
│   └── services/
├── main.py              # 入口文件
├── requirements.txt     # 依赖列表
├── render.yaml         # Render配置（可选）
├── Procfile            # 启动命令（可选）
├── .env                # 环境变量模板
└── README.md           # 说明文档
```

**不需要上传**:
- `venv/` - 虚拟环境
- `__pycache__/` - Python缓存
- `uploads/` - 本地上传文件
- `test_data/` - 测试数据
- `*.db` - 本地数据库文件

### 环境变量配置

在Render控制台设置以下环境变量：

| 变量名 | 说明 | 示例 |
|--------|------|------|
| SECRET_KEY | JWT密钥（必须） | 随机32位字符串 |
| DATABASE_URL | 数据库连接（可选） | sqlite+aiosqlite:///./app.db |
| CORS_ORIGINS | 允许的跨域来源 | ["https://yourapp.com"] |

### 数据库选择

**开发环境**: SQLite（默认）
- 简单易用，无需额外配置
- 适合小规模应用

**生产环境**: PostgreSQL（推荐）
- 在Render创建PostgreSQL数据库
- 复制数据库URL到环境变量
- 修改 `requirements.txt`:
  ```
  # 替换
  databases[asyncpg]==0.8.0
  # 为
  asyncpg==0.29.0
  sqlalchemy[asyncio]==2.0.25
  ```

## 🎯 核心功能

### Excel处理逻辑

1. **自动识别会计月列**: 支持"会计月"、"会计期间"、"月份"等列名
2. **智能识别数值列**: 自动检测需要汇总的数值列
3. **按月分组汇总**: 对同一会计月的所有数值列求和
4. **生成汇总表格**: 输出按会计月汇总后的Excel文件

### API接口

- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/login` - 用户登录
- `GET /api/v1/auth/profile` - 获取用户信息
- `POST /api/v1/files/upload` - 上传Excel文件
- `POST /api/v1/files/process` - 处理文件（汇总）
- `GET /api/v1/files/preview/{file_id}` - 预览文件
- `GET /api/v1/files/download/{file_id}` - 下载文件
- `GET /api/v1/files/history` - 历史记录
- `DELETE /api/v1/files/{file_id}` - 删除文件
- `GET /api/v1/admin/users` - 管理员查看用户列表
- `POST /api/v1/admin/users` - 管理员创建用户
- `PATCH /api/v1/admin/users/{user_id}` - 管理员更新用户
- `DELETE /api/v1/admin/users/{user_id}` - 管理员删除用户
- `GET /api/v1/admin/files` - 管理员查看文件列表
- `PATCH /api/v1/admin/files/{file_id}` - 管理员更新文件备注/状态
- `DELETE /api/v1/admin/files/{file_id}` - 管理员删除文件
- `POST /api/v1/admin/files/batch-delete` - 管理员批量删除文件
- `GET /api/v1/admin/stats` - 后台统计
- `GET /api/v1/admin/cleanup/config` - 清理配置
- `POST /api/v1/admin/cleanup/run` - 手动触发清理
- `POST /api/v1/ai/chat` - 机器人对话（使用服务端 AI_API_KEY）

## 🔧 技术栈

- **框架**: FastAPI 0.109.0
- **数据库**: SQLAlchemy + SQLite/PostgreSQL
- **认证**: JWT (python-jose)
- **Excel处理**: pandas + openpyxl
- **异步**: asyncio + aiofiles

## 📝 开发说明

### 项目结构

```
fastapi/
├── app/
│   ├── api/v1/          # API路由
│   │   ├── auth.py      # 认证接口
│   │   └── files.py     # 文件接口
│   ├── core/            # 核心配置
│   │   ├── config.py    # 配置管理
│   │   ├── database.py  # 数据库连接
│   │   └── security.py  # 安全认证
│   ├── models/          # 数据模型
│   │   ├── user.py      # 用户模型
│   │   └── file.py      # 文件模型
│   ├── schemas/         # 数据模式
│   │   ├── user.py      # 用户模式
│   │   ├── file.py      # 文件模式
│   │   └── response.py  # 响应模式
│   └── services/        # 业务逻辑
│       └── excel_processor.py  # Excel处理
├── main.py              # 应用入口
└── requirements.txt     # 依赖管理
```

## 📄 许可证

MIT License
