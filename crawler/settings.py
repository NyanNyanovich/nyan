BOT_NAME = "telegram_crawler"
SPIDER_MODULES = ["crawler.spiders"]
NEWSPIDER_MODULE = "crawler.spiders"
USER_AGENT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
ROBOTSTXT_OBEY = False
CONCURRENT_REQUESTS = 32
DOWNLOAD_DELAY = 0.3
RANDOMIZE_DOWNLOAD_DELAY = True
TELNETCONSOLE_ENABLED = False
ITEM_PIPELINES = {
    "crawler.pipelines.MongoPipeline": 300,
}
DNS_RESOLVER = "scrapy.resolver.CachingHostnameResolver"
LOG_LEVEL = "INFO"
