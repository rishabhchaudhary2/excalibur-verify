import scrapy
import re


class GNews(scrapy.Spider):
    name = "gnews_search"
    search_query: str  # This is a type hint to suppress warnings in the IDE

    custom_settings = {
        "LOG_ENABLED": True,
        "DOWNLOAD_TIMEOUT": 30
    }

    def start_requests(self):
        yield scrapy.Request(
            url = f"https://news.google.com/search?q={self.search_query}",
            callback = self.parse,
        )

    def parse(self, response: scrapy.http.Response):
        anchor = list(filter(lambda x: len(x[1]) > 0, re.findall(r'"\./articles/(.*?)".*?>(.*?)</a>', response.text)))[:10]
        for tag in anchor:
            print("Following:", tag[0])
            yield response.follow(
                f"https://news.google.com/articles/{tag[0]}",
                callback = self.process_redirects
            )
            print("Followed:", tag[0])

    def process_redirects(self, response: scrapy.http.Response):
        article_url = re.findall(r'Opening.*?href="(.*?)"', response.text.replace("\n", ""))[0]
        print("Resolving:", article_url)
        yield response.follow(
            article_url,
            callback = self.parse_article
        )
        print("Resolved:", article_url)

    def parse_article(self, response: scrapy.http.Response):
        print("Parsing:", response.url)
        yield {
            "title": response.css("h1::text").get(),
            "content": "\n".join(response.css("p::text").getall()),
            "url": response.url,
            "source": "gnews"
        }
        print("Parsed:", response.url)
