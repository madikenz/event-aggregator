BOT_NAME = "crawler"

SPIDER_MODULES = ["crawler.spiders"]
NEWSPIDER_MODULE = "crawler.spiders"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Scrapy-Playwright Config
# Dowload Handlers
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "timeout": 60 * 1000,  # 60 seconds
}

# Browser Context
PLAYWRIGHT_CONTEXT_ARGS = {
    "viewport": {"width": 1920, "height": 1080},
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

# Pipelines
ITEM_PIPELINES = {
   "crawler.pipelines.DatabasePipeline": 300,
}

# Concurrency
CONCURRENT_REQUESTS = 16

# Logging
LOG_LEVEL = 'INFO'

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HTTPERROR_ALLOWED_CODES = [403, 404, 429, 500]
