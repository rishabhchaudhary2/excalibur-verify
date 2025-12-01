import multiprocessing
import json
import os

from aiohttp import web

from scrapy import signals
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from scraper.spiders.gnews import GNews

from sentence_transformers import SentenceTransformer, util
import re

# from transformers import pipeline

app = web.Application()
router = web.RouteTableDef()


def eng_verify(_news):
    return (len(re.findall(r'[a-zA-Z]', _news)) / len(_news)) > 0.75


def run_crawler(query):
    process = CrawlerProcess(settings = get_project_settings())

    data = []

    def scrape_finished(item):
        data.append(item)

    process.crawl(GNews, search_query = query)

    for crawler in process.crawlers:
        crawler.signals.connect(
            scrape_finished,
            signal = signals.item_scraped
        )

    process.start()

    return data


def search_news(query):
    with multiprocessing.Pool() as pool:
        data = pool.map(run_crawler, [query, ])
        if not data[0]:
            return [[0]]

        calculated = pool.map(calculate_query, [(data[0], query), ])

        return calculated


def calculate_query(args):
    print(args)
    # summarizer = pipeline("summarization", model = "facebook/bart-large-cnn")
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

    def fmt_news(_news):
        # first layer filter
        _news = _news.replace("\n", " ")
        _news = re.sub(' +', ' ', _news).strip()

        # summarize
        # _news = summarizer(_news[:2048], max_length = 256, min_length = 50, do_sample = False)[0]["summary_text"]

        return _news

    news_res, data = args
    fmt_content = [fmt_news(n["content"]) for n in news_res if len(n["content"]) > 1000 and eng_verify(n["content"]) and n['title']]
    fmt_title = [n["title"] for n in news_res if len(n["content"]) > 1000 and eng_verify(n["content"])]
    print("Content formatted")

    if len(fmt_content) == 0:
        return 0, 0, None

    title_embedding = model.encode(fmt_title)
    query_embedding = model.encode(data)
    passage_embedding = model.encode(fmt_content)
    print("Embeddings calculated")

    title_sim = []
    passage_sim = []
    title_int_sim = get_intern_sim(title_embedding)
    passage_int_sim = get_intern_sim(passage_embedding)

    for title in title_embedding:
        title_sim.append(util.cos_sim(query_embedding, title))

    for passage in passage_embedding:
        passage_sim.append(util.cos_sim(query_embedding, passage))

    nres = float(sum(passage_sim) / len(passage_sim))
    tres = float(sum(title_sim) / len(title_sim))

    if len(fmt_content) > 5:
        total = 0.4 * nres + 0.2 * tres + 0.2 * title_int_sim + 0.2 * passage_int_sim
    else:
        total = 0.7 * nres + 0.3 * tres

    print("Similarity calculated")
    print(nres, tres, title_int_sim, passage_int_sim)
    print(total)

    norm = [float(ten) for ten in passage_sim]

    return float(total), news_res[norm.index(max(norm))]


def get_intern_sim(tensor):
    intern_sim = []

    for i in range(len(tensor)):
        for j in range(len(tensor) - i):
            intern_sim.append(util.cos_sim(tensor[i], tensor[i + j]))

    return float(sum(intern_sim) / len(intern_sim))


@router.post('/api/text')
async def index(request):
    text = (await request.json())['text']
    print("search request received ", text)

    res = search_news(text)

    return web.Response(text = json.dumps(res))


@router.get('/')
async def index(request):
    return web.FileResponse('public/front.html')


local_dir = os.path.join(os.path.dirname(__file__), "public")
app.router.add_static('/public', local_dir)

app.add_routes(router)
web.run_app(app)
