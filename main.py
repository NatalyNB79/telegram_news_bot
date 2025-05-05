"""
Скрипт для парсинга новостей и отправки их в Telegram канал.
"""

import config

print(config.TELEGRAM_TOKEN)


from html import escape
import traceback
import asyncio
import feedparser
import requests
from bs4 import BeautifulSoup
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from config import TELEGRAM_TOKEN, TELEGRAM_CHANNEL_ID

bot = Bot(token=TELEGRAM_TOKEN)


# --- ОЧИСТКА СТАТЬИ ОТ МУСОРА ---
async def fetch_full_article(url):
    """
    Получение очищенного текста статьи по URL.
    """
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        article_text = ""

        # Пробуем найти основной article-блок
        article = soup.find("article")

        if not article:
            for class_name in [
                "article__text",
                "article-content",
                "content",
                "main-text",
            ]:
                article = soup.find("div", class_=class_name)
                if article:
                    break

        if article:
            paragraphs = article.find_all("p")
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and not any(
                    phrase in text.lower()
                    for phrase in ["регистрация", "перейдите по ссылке", "комментарий"]
                ):
                    article_text += text + "\n"
        else:
            # fallback: очищаем весь текст страницы
            raw_text = soup.get_text(separator="\n")
            lines = raw_text.splitlines()
            clean_lines = []
            for line in lines:
                line = line.strip()
                if (
                    len(line) > 30
                    and not line.lower().startswith("регистрация")
                    and "подписка" not in line.lower()
                    and "комментарий" not in line.lower()
                ):
                    clean_lines.append(line)
            article_text = "\n".join(clean_lines[:10])  # максимум 10 строк

        return article_text.strip()

    except (requests.exceptions.RequestException, Exception) as e:
        print(f"Error fetching full article: {e}")
        traceback.print_exc()
        return None


# --- ПОИСК ИЗОБРАЖЕНИЯ ---
async def fetch_image(link):
    """
    Поиск изображения в статье.
    """
    try:
        response = requests.get(link, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            return og_image["content"]

        img = soup.find("img")
        if img and img.get("src"):
            return img["src"]

    except requests.exceptions.RequestException as e:
        print(f"Error fetching image: {e}")
        traceback.print_exc()

    return None


# --- ПАРСИНГ RSS ---
async def fetch_rss_news(url):
    """
    Получение новостей из RSS-канала.
    """
    feed = feedparser.parse(url)
    news = []
    for entry in feed.entries[:5]:
        summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
        news.append(
            {
                "title": entry.title,
                "link": entry.link,
                "summary": summary,
            }
        )
    return news


# --- ОТПРАВКА В TELEGRAM ---
async def post_news():
    """
    Получение и отправка новостей в Telegram.
    """
    rss_feeds = [
        "https://rssexport.rbc.ru/rbcnews/news/stream.rss",
        "https://ria.ru/export/rss2/index.xml",
        "https://tass.ru/rss/v2.xml",
        "https://www.vedomosti.ru/rss/news",
        "https://www.kommersant.ru/RSS/news",
    ]

    for rss_url in rss_feeds:
        print(f"Fetching news from: {rss_url}")
        news_items = await fetch_rss_news(rss_url)

        for item in news_items:
            print(f"Processing: {item['title']}")
            full_article = await fetch_full_article(item["link"])
            image_url = await fetch_image(item["link"])

            title_safe = escape(item["title"])

            if full_article:
                article_safe = escape(full_article[:1500])  # ограничим длину
                text = f"📰 <b>{title_safe}</b>\n\n{article_safe}"
            else:
                summary_safe = escape(item["summary"][:1000])
                text = f"📰 <b>{title_safe}</b>\n\n{summary_safe}"

            comment_button = InlineKeyboardButton(
                "Оставить комментарий", url=f"{item['link']}#comments"
            )
            keyboard = InlineKeyboardMarkup([[comment_button]])

            try:
                if image_url:
                    await asyncio.sleep(3)
                    await bot.send_photo(
                        chat_id=TELEGRAM_CHANNEL_ID,
                        photo=image_url,
                        reply_markup=keyboard,
                    )
                    await asyncio.sleep(1)
                    await bot.send_message(
                        chat_id=TELEGRAM_CHANNEL_ID,
                        text=text[:4096],
                        parse_mode="HTML",
                        reply_markup=keyboard,
                    )
                else:
                    await bot.send_message(
                        chat_id=TELEGRAM_CHANNEL_ID,
                        text=text[:4096],
                        parse_mode="HTML",
                        reply_markup=keyboard,
                    )
                    await asyncio.sleep(2)

                print(f"✅ Sent: {item['title']}")

            except Exception as e:
                print(f"Error sending news: {e}")
                traceback.print_exc()


# --- ЗАПУСК ---
async def main():
    """
    Основная функция для запуска парсинга новостей и их отправки в Telegram.
    """
    await post_news()


if __name__ == "__main__":
    asyncio.run(main())
