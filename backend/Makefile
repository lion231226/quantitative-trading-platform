.PHONY: help install dev test lint format clean build run

help: ## 显示帮助信息
	@echo "可用命令:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 安装依赖
	pip install -r requirements.txt
	pip install -e .

dev: ## 启动开发服务器
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

test: ## 运行测试
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing

test-fast: ## 运行快速测试（跳过慢测试）
	pytest tests/ -v -m "not slow"

test-unit: ## 运行单元测试
	pytest tests/unit/ -v

test-integration: ## 运行集成测试
	pytest tests/integration/ -v

lint: ## 代码检查
	flake8 app/
	mypy app/
	black --check app/
	isort --check-only app/

format: ## 格式化代码
	black app/
	isort app/

lint-fix: ## 修复代码格式问题
	$(MAKE) format

clean: ## 清理缓存文件
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf htmlcov/
	rm -rf .coverage

build: ## 构建Docker镜像
	docker build -t quant-trading-backend .

run: ## 生产模式运行
	uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

shell: ## 启动Python shell
	python -i -c "from app.main import app; from app.core.config import settings"

migrate: ## 运行数据库迁移
	alembic upgrade head

migrate-create: ## 创建新的数据库迁移
	alembic revision --autogenerate -m "$(MSG)"

seed: ## 初始化数据库数据
	python scripts/seed_data.py

check-all: ## 运行所有检查
	$(MAKE) lint
	$(MAKE) test

ci: ## CI/CD流程
	$(MAKE) clean
	$(MAKE) install
	$(MAKE) lint
	$(MAKE) test-fast

docs: ## 生成API文档
	open http://localhost:8000/docs

logs: ## 查看应用日志
	tail -f logs/app.log

docker-dev: ## Docker开发环境
	docker-compose -f docker-compose.dev.yml up --build

docker-prod: ## Docker生产环境
	docker-compose up -d --build

setup-dev: ## 初始化开发环境
	python -m venv venv
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && pip install -r requirements.txt
	. venv/bin/activate && pip install -e .
	cp .env.example .env
	@echo "开发环境设置完成！请编辑 .env 文件配置环境变量"

pre-commit: ## 安装pre-commit钩子
	pre-commit install

check-deps: ## 检查依赖安全性
	pip-audit

profile: ## 性能分析
	python -m cProfile -o profile.stats main.py

benchmark: ## 运行性能基准测试
	python scripts/benchmark.py