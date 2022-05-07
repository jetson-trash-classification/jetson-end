import web
from jetson_client import jetson_client 

urls = ("/(.*)", "index")

class index:
    """
    处理主机post请求
    """

    def POST(self, data):
        """
        post修改jetson设置
        """
        if client is not None:
            for key, value in data:
                client[key] = value


if __name__ == "__main__":
    client = jetson_client()
    app = web.application(urls, globals())
    app.add_processor(client.main_task)
    app.run()
