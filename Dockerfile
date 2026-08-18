# CUHK IDADM Course Helper - Docker 镜像
# 基礎鏡像：uv 官方鏡像（自帶 uv + Python 3.14）
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

# 關閉 Streamlit 自動打開瀏覽器、避免容器內無頭環境報錯
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV UV_LINK_MODE=copy

WORKDIR /app

# 先只複製依賴清單，充分利用 Docker layer 快取
# （依賴不變時重新 build 不會重裝依賴）
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# 再複製應用程式碼與靜態資料
COPY main.py ./
COPY app ./app
COPY src ./src
COPY data ./data

# 注意：故意不複製 .streamlit/secrets.toml（含 Supabase 密鑰）
# 部署時透過 volume 掛載或環境變數注入，見 docker-compose.yml

EXPOSE 8501

# 健康檢查（用 Python 而非 curl，slim 鏡像沒有 curl）
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

ENTRYPOINT ["uv", "run", "streamlit", "run", "main.py", \
            "--server.port=8501", \
            "--server.address=0.0.0.0", \
            "--server.headless=true"]
