-- 应用程序相关表
-- 创建时间: 2025-11-05
-- 描述: 添加应用程序特定的表结构

-- 创建应用配置表
CREATE TABLE IF NOT EXISTS app_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    config_name VARCHAR(100) NOT NULL,
    config_data JSONB NOT NULL DEFAULT '{}',
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, config_name)
);

-- 创建任务队列表
CREATE TABLE IF NOT EXISTS task_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_type VARCHAR(50) NOT NULL,
    task_data JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    scheduled_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    result JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建通知表
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    notification_type VARCHAR(50) DEFAULT 'info',
    is_read BOOLEAN DEFAULT false,
    action_url VARCHAR(500),
    metadata JSONB DEFAULT '{}',
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建文件存储表
CREATE TABLE IF NOT EXISTS file_storage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100),
    file_hash VARCHAR(64),
    is_public BOOLEAN DEFAULT false,
    download_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建API密钥表
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key_name VARCHAR(100) NOT NULL,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    permissions JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_app_configs_user_id ON app_configs(user_id);
CREATE INDEX IF NOT EXISTS idx_app_configs_name ON app_configs(config_name);
CREATE INDEX IF NOT EXISTS idx_app_configs_default ON app_configs(is_default);

CREATE INDEX IF NOT EXISTS idx_task_queue_status ON task_queue(status);
CREATE INDEX IF NOT EXISTS idx_task_queue_type ON task_queue(task_type);
CREATE INDEX IF NOT EXISTS idx_task_queue_priority ON task_queue(priority DESC);
CREATE INDEX IF NOT EXISTS idx_task_queue_scheduled ON task_queue(scheduled_at);

CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(notification_type);
CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_file_storage_user_id ON file_storage(user_id);
CREATE INDEX IF NOT EXISTS idx_file_storage_hash ON file_storage(file_hash);
CREATE INDEX IF NOT EXISTS idx_file_storage_public ON file_storage(is_public);
CREATE INDEX IF NOT EXISTS idx_file_storage_created ON file_storage(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active);
CREATE INDEX IF NOT EXISTS idx_api_keys_expires ON api_keys(expires_at);

-- 添加更新时间触发器
CREATE TRIGGER update_app_configs_updated_at BEFORE UPDATE ON app_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_file_storage_updated_at BEFORE UPDATE ON file_storage
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 创建任务状态枚举约束
ALTER TABLE task_queue ADD CONSTRAINT chk_task_status
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled'));

-- 创建通知类型约束
ALTER TABLE notifications ADD CONSTRAINT chk_notification_type
    CHECK (notification_type IN ('info', 'success', 'warning', 'error', 'system'));

-- 插入初始配置
INSERT INTO system_config (config_key, config_value, config_type, description, is_public) VALUES
('task_queue_max_attempts', '3', 'integer', '任务队列最大重试次数', false),
('file_max_size', '104857600', 'integer', '文件最大大小（字节）', false),
('api_key_default_expires_days', '365', 'integer', 'API密钥默认过期天数', false),
('notification_retention_days', '30', 'integer', '通知保留天数', false)
ON CONFLICT (config_key) DO NOTHING;

-- 记录当前迁移
INSERT INTO schema_migrations (version, description, execution_time_ms) VALUES
('002', 'Add application tables', 0)
ON CONFLICT (version) DO NOTHING;