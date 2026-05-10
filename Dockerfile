FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量，指定编码
ENV PYTHONIOENCODING=utf-8
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY main.py config.py auth.py proxy.py pancheck.py ./

# 创建非root用户运行应用
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser

# 暴露端口
EXPOSE 1566

# 启动命令
CMD ["gunicorn", "-k", "gevent", "-w", "2", "-b", "0.0.0.0:1566", "main:app"]
