# backend/Dockerfile

# 使用官方 Python 镜像作为基础
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装依赖
COPY ./backend/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY ./backend /app

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
