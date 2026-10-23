# 部署说明（Streamlit Cloud）

## 一、推送到 GitHub

在 GitHub 新建一个空仓库（不勾选 README），然后在本仓库执行：

```bash
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git branch -M main
git push -u origin main
```

> `.env`（含真实 API key）和 `data/raw/`（真实脱敏数据）已被 `.gitignore` 忽略，**不会**被提交。
> 仓库里只有 `.env.example` 占位符和 `data/sample/` 模拟数据。

## 二、在 Streamlit Cloud 部署

1. 打开 https://share.streamlit.io ，用 GitHub 账号登录。
2. 点 **New app** → 选择刚推送的仓库 → Branch `main` → **Main file path** 填 `app.py`。
3. 点 **Deploy**，平台会按 `requirements.txt` 自动安装依赖并启动。

## 三、配置密钥（关键）

部署后，进入 App 的 **Settings → Secrets**，添加（真实 key 只放这里、不进仓库）：

```toml
LLM_API_KEY = "sk-xxxx"
LLM_BASE_URL = "https://api.deepseek.com"
LLM_MODEL = "deepseek-chat"
```

保存后 App 自动重启，页面底部的「AI 数据洞察」即可使用。

## 四、说明

- 未配置密钥时，App 仍可正常展示看板，只是 AI 洞察会提示「未配置 API」。
- `data/sample/` 是模拟数据，App 启动时自动加载用于演示；真实数据放本地 `data/raw/`（不上传）。
- 如需固定 Python 版本，可在仓库根目录加 `runtime.txt`（内容如 `3.11`）。
