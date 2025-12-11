/**
 * 应用全局配置
 * 统一管理后端 API 地址等配置项
 * 
 * 环境变量配置说明：
 * - 开发环境: .env 文件中配置 VITE_API_BASE_URL
 * - 生产环境: .env.production 文件中配置 VITE_API_BASE_URL
 */

// 后端 API 基础地址（从环境变量读取，回退到默认值）
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// API 端点
export const API_ENDPOINTS = {
    UPLOAD: `${API_BASE_URL}/api/upload`,
    CHECK_PREMADE: `${API_BASE_URL}/api/check-premade`,
    WHERE_TO_EAT: `${API_BASE_URL}/api/where-to-eat`,
    CALORIES: `${API_BASE_URL}/api/calories`,
    HISTORY: `${API_BASE_URL}/api/history`,
};

export default {
    API_BASE_URL,
    API_ENDPOINTS,
};
