"""
Скрипт для парсинга новостей и отправки их в Telegram канал.
"""

from html import escape

import sys
import os

sys.path.append(os.path.abspath("."))
import os

print(os.getcwd())


import traceback
import asyncio
import feedparser
import requests
from bs4 import BeautifulSoup
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from config import TELEGRAM_TOKEN, TELEGRAM_CHANNEL_ID

bot = Bot(token=TELEGRAM_TOKEN)


# Получение полного текста статьи
async def fetch_full_article(url):
    """
    Получение полного текста статьи по URL.

    Args:
        url (str): Ссылка на статью.

    Returns:
        str: Полный текст статьи.
    """
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        article_text = ""
        article = soup.find("article")

        if article:
            paragraphs = article.find_all("p")
            for paragraph in paragraphs:
                article_text += paragraph.get_text() + "\n"
        else:
            article_text = soup.get_text()

        return article_text.strip()

    except requests.exceptions.RequestException as e:
        print(f"Error fetching full article: {e}")
        traceback.print_exc()
    return None


# Попытка найти изображение в статье
async def fetch_image(link):
    """
    Попытка найти изображение в статье по ссылке.

    Args:
        link (str): Ссылка на статью.

    Returns:
        str: Ссылка на изображение.
    """
    try:
        response = requests.get(link, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        # Сначала ищем <meta property="og:image">
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            return og_image["content"]

        # Если не найдено — пробуем найти первое изображение
        img = soup.find("img")
        if img and img.get("src"):
            return img["src"]

    except requests.exceptions.RequestException as e:
        print(f"Error fetching image: {e}")
        traceback.print_exc()
    return None


# Получение новостей из RSS
async def fetch_rss_news(url):
    """
    Получение новостей из RSS-канала.

    Args:
        url (str): Ссылка на RSS-канал.

    Returns:
        list: Список новостей.
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


# Отправка новостей в Telegram
async def post_news():
    """
    Получение новостей из нескольких RSS-каналов и отправка их в Telegram.
    """
    rss_feeds = [
        "https://rssexport.rbc.ru/rbcnews/news/stream.rss",  # РБК
        "https://ria.ru/export/rss2/index.xml",  # РИА Новости
        "https://tass.ru/rss/v2.xml",  # ТАСС
        "https://www.vedomosti.ru/rss/news",  # Ведомости
        "https://www.kommersant.ru/RSS/news",  # Коммерсантъ
    ]

    for rss_url in rss_feeds:
        print(f"Fetching news from: {rss_url}")
        news_items = await fetch_rss_news(rss_url)

        for item in news_items:
            print(f"Processing news item: {item['title']}")
            full_article = await fetch_full_article(item["link"])
            image_url = await fetch_image(item["link"])

            if full_article:
                title_safe = escape(item["title"])
                article_safe = escape(full_article)
                text = f"📰 <b>{title_safe}</b>\n\n{article_safe}"
            else:
                title_safe = escape(item["title"])
                summary_safe = escape(item["summary"])
                text = f"📰 <b>{title_safe}</b>\n\n{summary_safe}"

            # Кнопка для комментариев
            comment_button = InlineKeyboardButton(
                "Оставить комментарий", url=f"{item['link']}#comments"
            )
            keyboard = InlineKeyboardMarkup([[comment_button]])

            try:
                if image_url:
                    # Сначала фото без текста
                    await asyncio.sleep(180)
                    await bot.send_photo(
                        chat_id=TELEGRAM_CHANNEL_ID,
                        photo=image_url,
                        reply_markup=keyboard,
                    )
                    # Потом полный текст
                    await asyncio.sleep(180)
                    await bot.send_message(
                        chat_id=TELEGRAM_CHANNEL_ID,
                        text=text[:4096],
                        parse_mode="HTML",
                        reply_markup=keyboard,
                    )
                else:
                    # Без фото — просто текст
                    await bot.send_message(
                        chat_id=TELEGRAM_CHANNEL_ID,
                        text=text[:4096],
                        parse_mode="HTML",
                        reply_markup=keyboard,
                    )
                    await asyncio.sleep(180)
                    
                print(f"Sent news: {item['title']}")
            except (requests.exceptions.RequestException, AttributeError) as e:
                print(f"Error sending news: {e}")
                traceback.print_exc()


# Запуск
async def main():
    """
    Главная функция для запуска парсинга и отправки новостей.
    """
    await post_news()


if __name__ == "__main__":
    asyncio.run(main())
