# backend/Dockerfile

# 使用官方 Python 镜像作为基础
FROM python:3.10-slim

# 设置环境变量，防止 Python 写入 .pyc 文件和缓冲输出
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 设置工作目录
WORKDIR /app

# 安装依赖
COPY ./backend/requirements.txt /app/
# 使用国内镜像源加速
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

# 【修正】: 将整个 backend 目录复制到镜像的 /app 目录中
# 这确保了镜像是自包含的，包含了所有代码
COPY ./backend/ /app/

# 暴露端口 (主要为 backend 服务)
EXPOSE 8000

# 默认的启动命令 (将被 docker-compose 覆盖)
# 我们在 docker-compose 中定义 CMD，所以这里可以不写