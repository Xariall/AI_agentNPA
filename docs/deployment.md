# Деплой на Railway

## Требования

- Аккаунт [Railway](https://railway.app)
- Qdrant Cloud (отдельный кластер)
- Telegram Bot Token

---

## Деплой

```bash
cd backend
railway up --detach
```

---

## Переменные окружения

```bash
railway variables --set "GEMINI_API_KEY=..."
railway variables --set "TELEGRAM_BOT_TOKEN=..."
railway variables --set "QDRANT_URL=https://your-cluster.qdrant.io"
railway variables --set "QDRANT_API_KEY=..."
railway variables --set "LLM_BACKEND=gemini"

# Экономия RAM (~512MB лимит на Railway)
railway variables --set "ENABLE_RERANKING=false"
railway variables --set "EMBEDDING_MODEL=intfloat/multilingual-e5-small"
```

Посмотреть текущие:

```bash
railway variables
```

---

## Важно: модели и коллекции

На Railway используется `e5-small` (384d) вместо `e5-large` (1024d) из-за ограничений RAM.  
Это **разные коллекции** в Qdrant — нельзя использовать одну коллекцию для разных моделей.

| Окружение | Embedding model | Qdrant collection | Reranking |
|-----------|----------------|-------------------|-----------|
| Local dev | `e5-large` (1024d) | `npa` | ✅ включён |
| Railway | `e5-small` (384d) | `npa_small` | ❌ отключён |

---

## Healthcheck

Railway проверяет `/api/health` с таймаутом 120s (настроено в `railway.toml`).

BM25 грузится при старте (~5с), health endpoint доступен сразу.

---

## Логи

```bash
railway logs
railway logs --tail
```
