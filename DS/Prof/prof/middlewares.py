# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy import signals

# useful for handling different item types with a single interface
from itemadapter import is_item, ItemAdapter

import os, tempfile, time, sys, logging
logger = logging.getLogger(__name__)

import dryscrape
import pytesseract
from PIL import Image

from scrapy.downloadermiddlewares.redirect import RedirectMiddleware

class ProfSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class ProfDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class ThreatDefenceRedirectMiddleware(RedirectMiddleware):
    def __init__(self, settings):
        super().__init__(settings)

        # start xvfb to support headless scraping
        if 'linux' in sys.platform:
            dryscrape.start_xvfb()

        self.dryscrape_session = dryscrape.Session(base_url='https://scholar.google.com')
        for key, value in settings['DEFAULT_REQUEST_HEADERS'].items():
            # seems to be a bug with how webkit-server handles accept-encoding
            if key.lower() != 'accept-encoding':
                self.dryscrape_session.set_header(key, value)

    def _redirect(self, redirected, request, spider, reason):
        # act normally if this isn't a threat defense redirect
        if not self.is_threat_defense_url(redirected.url):
            return super()._redirect(redirected, request, spider, reason)

        logger.debug(f'Threat defense triggered for {request.url}')
        request.cookies = self.bypass_threat_defense(redirected.url)
        request.dont_filter = True # prevents the original link being marked a dupe
        return request

    def is_threat_defense_url(self, url):
        return '://scholar.google.co.in/citations?user=' in url

    def bypass_threat_defense(self, url=None):
        # only navigate if any explicit url is provided
        if url:
            self.dryscrape_session.visit(url)

        # solve the captcha if there is one
        captcha_images = self.dryscrape_session.css('img[src *= captcha]')
        if len(captcha_images) > 0:
            return self.solve_captcha(captcha_images[0])

        # click on any explicit retry links
        retry_links = self.dryscrape_session.css('a[href *= threat_defence]')
        if len(retry_links) > 0:
            return self.bypass_threat_defense(retry_links[0].get_attr('href'))

        # otherwise, we're on a redirect page so wait for the redirect and try again
        self.wait_for_redirect()
        return self.bypass_threat_defense()

    def wait_for_redirect(self, url = None, wait = 0.1, timeout=10):
        url = url or self.dryscrape_session.url()
        for i in range(int(timeout//wait)):
            time.sleep(wait)
            if self.dryscrape_session.url() != url:
                return self.dryscrape_session.url()
        logger.error(f'Maybe {self.dryscrape_session.url()} isn\'t a redirect URL?')
        raise Exception('Timed out on the redirect page.')

    def solve_captcha(self, img, width=1280, height=800):
        # take a screenshot of the page
        self.dryscrape_session.set_viewport_size(width, height)
        filename = tempfile.mktemp('.png')
        self.dryscrape_session.render(filename, width, height)

        # inject javascript to find the bounds of the captcha
        js = 'document.querySelector("img[src *= captcha]").getBoundingClientRect()'
        rect = self.dryscrape_session.eval_script(js)
        box = (int(rect['left']), int(rect['top']), int(rect['right']), int(rect['bottom']))

        # solve the captcha in the screenshot
        image = Image.open(filename)
        os.unlink(filename)
        captcha_image = image.crop(box)
        captcha = pytesseract.image_to_string(captcha_image)
        logger.debug(f'Solved the captcha: "{captcha}"')

        # submit the captcha
        input = self.dryscrape_session.xpath('//input[@id = "solve_string"]')[0]
        input.set(captcha)
        button = self.dryscrape_session.xpath('//button[@id = "button_submit"]')[0]
        url = self.dryscrape_session.url()
        button.click()

        # try again if it we redirect to a threat defense URL
        if self.is_threat_defense_url(self.wait_for_redirect(url)):
            return self.bypass_threat_defense()

        # otherwise return the cookies as a dict
        cookies = {}
        for cookie_string in self.dryscrape_session.cookies():
            if 'domain=scholar.google.com' in cookie_string:
                key, value = cookie_string.split(';')[0].split('=')
                cookies[key] = value
        return cookies