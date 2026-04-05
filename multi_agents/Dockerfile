# BettaFish LangGraph Multi-Agent Dockerfile
# 用于部署到 ALB 平台的 LangGraph 舆情分析智能体

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖（用于 weasyprint PDF 生成等）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-noto-cjk \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 复制项目文件
COPY . .

# 创建输出目录
RUN mkdir -p /app/outputs /app/logs

# 设置默认环境变量
ENV HOST=0.0.0.0 \
    PORT=18019 \
    OPENAI_BASE_URL=http://192.168.195.195:18011/v1 \
    ALB_MCP_URL=http://192.168.195.195:18012/api/mcp \
    RETRIEVER=duckduckgo \
    REPORT_OUTPUT_DIR=/app/outputs \
    DEBUG=0

# 暴露端口
EXPOSE 18019

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:18019/health || exit 1

# 启动 LangGraph 服务
WORKDIR /app/multi_agents
CMD ["langgraph", "up", "--host", "0.0.0.0", "--port", "18019"]
