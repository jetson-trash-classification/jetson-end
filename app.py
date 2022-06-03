from queue import Queue
import web, json, threading
import json
import jetson.inference, jetson.utils
from enum import Enum
import RPi.GPIO as GPIO
import time, requests, datetime

host_url = "http://192.168.137.1:3001/"  # 主机所在ip
position = "rKkwZHirl27G3XxrP62_s"  # jetson id

# 引脚种类
type_list = ["food", "hazardous", "recyclable", "residual"]


class jetson_state(Enum):
    IDEL = 1  # 空闲状态
    WAKEUP = 2  # 摄像头开启
    SLEEP = 3  # 摄像头关闭
    WORK = 4  # 拍照，识别，上传


# 引脚定义
pin_food = 31
pin_hazardous = 33
pin_recyclable = 35
pin_residual = 37
pin_sensor = 29
pin_button = 23

pin_out_list = [pin_food, pin_residual, pin_hazardous, pin_recyclable]
pin_in_list = [pin_sensor]

# 共享队列
que = Queue()

# 结果和引脚的映射
lid_map = [pin_food, pin_residual, pin_hazardous, pin_recyclable]


def get_curtime():
    """
    获取当前时间
    """
    cur_time = datetime.datetime.now()
    time_str = datetime.datetime.strftime(cur_time, "%Y-%m-%d %H:%M:%S")
    return time_str


def post_data(type, accuracy):
    """
    发送数据
    """
    header = {
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json",
    }
    data = {
        "time": get_curtime(),
        "position": position,
        "type": type,
        "accuracy": accuracy,
    }
    r = requests.post(
        url=host_url + "history", data=json.dumps(data), headers=header, timeout=60
    )

    if r.status_code is 200:
        print("Post done with state code 200...")
    else:
        print("Post err with state code %d..." % (r.status_code))


def put_data():
    """
    清空回收站点
    """
    header = {
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json",
    }
    requests.put(host_url + "history", data=position, headers=header)


class ShowState:
    def __init__(self, name) -> None:
        self.name = name

    def __enter__(self):
        print("Enter state: %s" % (self.name))

    def __exit__(self, e1, e2, e3):
        print("Exit state: %s" % (self.name))


class JetsonClient(threading.Thread):
    def __init__(self) -> None:
        threading.Thread.__init__(self)

        # 当前打开的盖子
        self.cur_lid = -1
        self.last_lid = -1

        # 设置状态表
        self.state_tlb = {
            jetson_state.IDEL: {
                GPIO.HIGH: jetson_state.WAKEUP,
                GPIO.LOW: jetson_state.IDEL,
            },
            jetson_state.WAKEUP: {
                GPIO.HIGH: jetson_state.WORK,
                GPIO.LOW: jetson_state.SLEEP,
            },
            jetson_state.WORK: {
                GPIO.HIGH: jetson_state.WORK,
                GPIO.LOW: jetson_state.SLEEP,
            },
            jetson_state.SLEEP: {
                GPIO.HIGH: jetson_state.IDEL,
                GPIO.LOW: jetson_state.IDEL,
            },
        }

        # 设置函数表
        self.func_tlb = {
            jetson_state.IDEL: self.idel,
            jetson_state.WAKEUP: self.wake_up,
            jetson_state.WORK: self.work,
            jetson_state.SLEEP: self.sleep,
        }

        # 设置初始状态
        self.state = jetson_state.IDEL

        self.init_net()
        self.init_gpio()
        self.init_settings()
        print("Jetson end init OK...")

    def open_lid(self, class_id):
        """
        选择一个垃圾盖子打开，如果之前有打开的，则清空之前的
        """
        self.last_lid = self.cur_lid
        self.cur_lid = lid_map[class_id]

        if self.last_lid != -1 and self.last_lid != self.cur_lid:
            # 如果之前有打开的盖子，则关闭打开的盖子
            GPIO.output(self.last_lid, GPIO.LOW)
            self.last_lid = -1

        GPIO.output(self.cur_lid, GPIO.HIGH)

        for i in range(10):
            print("Lid %d open %ds ...." % (self.cur_lid, i))
            time.sleep(1)

    def close_lid(self):
        """
        关闭所有垃圾盖子,只有在退出时调用, 如果是切换则调用open_lid
        """
        if self.last_lid != -1:
            GPIO.output(self.last_lid, GPIO.LOW)
            self.last_lid = -1
            print("Lid %d close..." % (self.last_lid))

        if self.cur_lid != -1:
            GPIO.output(self.cur_lid, GPIO.LOW)
            self.cur_lid = -1
            print("Lid %d close..." % (self.cur_lid))

    def init_net(self):
        # 创建网络
        try:
            self.net = jetson.inference.imageNet(
                "resnet18",
                [
                    "--model=/home/hgg/jetson-inference/python/training/classification/models/r50/resnet18.onnx",
                    "--input_blob=input_0",
                    "--output_blob=output_0",
                    "--labels=/home/hgg/jetson-inference/python/training/classification/data/label2.txt",
                ],
            )
            print("Net create done...")
        except Exception as e:
            print("Net create err: %s" % (str(e)))

    def init_gpio(self):
        """
        初始化GPIO引脚
        """
        try:
            GPIO.setmode(GPIO.BOARD)  # BOARD pin-numbering scheme
            GPIO.setup(pin_out_list, GPIO.OUT)
            GPIO.setup(pin_in_list, GPIO.IN)
            GPIO.output(pin_out_list, GPIO.LOW)

            # 设置按钮
            GPIO.setup(pin_button, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            GPIO.add_event_detect(pin_button, GPIO.RISING)  # 在通道上添加上升临界值检测
            GPIO.add_event_callback(pin_button, lambda x: self.clear_capacity())
            print("GPIO init done...")
        except Exception as e:
            print("GPIO init err: %s" % (str(e)))

    def init_settings(self):
        """
        初始化设置
        """
        try:
            res = requests.get(host_url + "settings", data="rKkwZHirl27G3XxrP62_s")
            res = json.loads(res.text)
            self.data = res
            print("Settings init done...")
        except Exception as e:
            print("Get err: %s" % (str(e)))

    def handle_input(self):
        # 获取最新的设置
        if not que.empty():
            res = que.get()
            for key, value in res["data"].items():
                if self.data["data"][key] != value:
                    print("Settings %s update to %s..." % (key, value))
                    self.data["data"][key] = value

    def clear_capacity(self):
        for type in type_list:
            self.data["data"][type + "Cur"] = 0

        put_data()
        print("Clear capacity done...")

    def is_full(self, class_id):
        # 判断垃圾桶是否装满
        cur = type_list[class_id] + "Cur"
        total = type_list[class_id] + "Capacity"
        return self.data["data"][cur] >= [10, 20, 30][self.data["data"][total]]

    def get_result(self):
        """
        捕捉100张图片, 统计出现频率最高的
        """
        num = 100  # 捕捉100张图片
        accuracy_sum = [0, 0, 0, 0]
        res_list = [0, 0, 0, 0]

        for i in range(num):
            img = self.camera.Capture()
            class_id, accuracy = self.net.Classify(img)
            res_list[class_id] += 1
            accuracy_sum[class_id] += accuracy

        res = res_list.index(max(res_list))
        accuracy = accuracy_sum[res] / num

        return res, accuracy

    def wake_up(self):
        """
        Create the Camera instance
        """
        with ShowState("wake up"):
            try:
                self.camera = jetson.utils.videoSource("csi://0")
            except Exception as e:
                print("Camera create err: %s" % (str(e)))

    def work(self):
        """
        拍照，识别并上传
        """
        with ShowState("work"):

            class_id, accuracy = self.get_result()

            type = type_list[class_id]

            # 如果精确度太低，则不认为是垃圾
            if accuracy < 0.5:
                self.close_lid()
                print("No trash detect, eixt...")
                return

            # 如果垃圾桶已满，则无法加入
            if self.is_full(class_id):
                self.close_lid()
                print("Trash class %s is full..." % (type))
                return

            print("classification result: %s ..." % (type))

            # 提交数据
            post_data(class_id, accuracy)

            # 修改当前容量
            self.data["data"][type + "Cur"] += 1
            self.open_lid(class_id)

    def sleep(self):
        with ShowState("sleep"):
            self.close_lid()
            del self.camera

    def idel(self):
        pass

    def run(self):
        """
        jetson主进程,
        输入: 当前的红外传感器值
        """
        while True:
            self.handle_input()
            input = GPIO.input(pin_sensor)  # 获取传感器最新的输入
            self.func_tlb[self.state]()
            self.state = self.state_tlb[self.state][input]

    def __del__(self):
        GPIO.cleanup()  # cleanup all GPIOs


class Server(threading.Thread):
    def run(self):
        urls = ("/", "Server")
        app = web.application(urls, globals())
        app.run()

    def POST(self):
        data = json.loads(web.data())
        que.put(data)


if __name__ == "__main__":
    Server().start()
    client = JetsonClient()
    client.start()
    while True:
        pass
