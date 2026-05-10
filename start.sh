#!/bin/bash

# 启动脚本
echo "正在启动 PansouAndPanCheck 服务..."

# 检查是否设置了必要的环境变量
if [ -z "$SEARCH_API_URL" ]; then
    echo "警告: SEARCH_API_URL 未设置，将使用默认值 http://127.0.0.1:8888"
fi

if [ -z "$CHECK_API_URL" ]; then
    echo "警告: CHECK_API_URL 未设置，将使用默认值 http://127.0.0.1/api/v1/links/check"
fi

# 启动应用
exec gunicorn -k gevent -w "${WORKERS:-2}" -b "${HOST:-0.0.0.0}:${PORT:-1566}" main:app
