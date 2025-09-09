# middlewares.py

import logging


class LogResponseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger(__name__)

    def __call__(self, request):
        # 处理请求
        response = self.get_response(request)

        # 处理响应
        print("**********************************")
        print("Response Status: %s", response.status_code)
        print("Response Headers: %s", response.items())

        return response
