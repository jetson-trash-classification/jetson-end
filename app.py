from queue import Queue
import web, json, threading, sys
import json
import jetson.inference, jetson.utils
from enum import Enum
import RPi.GPIO as GPIO
import time, requests, datetime

host_url = "http://192.168.137.1:3001/settings"  # 主机所在ip
position = "rKkwZHirl27G3XxrP62_s"  # jetson id

# 引脚种类
type_list = ["food", "residual", "hazardous", "recycle", "sensor"]


class jetson_state(Enum):
    IDEL = 1  # 空闲状态
    WAKEUP = 2  # 摄像头开启
    SLEEP = 3  # 摄像头关闭
    WORK = 4  # 拍照，识别，上传


# 引脚定义
pin_food = 31
pin_residual = 33
pin_hazardous = 35
pin_recycle = 37
pin_sensor = 29

que = Queue()


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
    r = requests.post(
        url=host_url,
        data={
            time: get_curtime(),
            position: position,
            type: type_list[type],
            accuracy: accuracy,
        },
    )

    if r.status_code is 200:
        print("Post done...")
    else:
        print("Post err...")


def open_lid(lid):
    """
    选择一个垃圾盖子打开
    """
    GPIO.output(lid, GPIO.HIGH)
    time.sleep(10)
    GPIO.output(lid, GPIO.LOW)


class jetson_client(threading.Thread):
    def __init__(self) -> None:
        threading.Thread.__init__(self)

        # 设置状态表
        self.state_tlb = {
            jetson_state.IDEL: {
                GPIO.HIGH: jetson_state.WAKEUP,
                GPIO.LOW: jetson_state.IDEL,
            },
            jetson_state.WAKEUP: {
                GPIO.HIGH: jetson_state.WAKEUP,
                GPIO.LOW: jetson_state.WAKEUP,
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
            jetson_state.IDEL: self.silence,
            jetson_state.WAKEUP: self.create_camera,
            jetson_state.WORK: self.capture,
            jetson_state.SLEEP: self.destroy_camera,
        }

        self.state = jetson_state.IDEL  # 设置初始状态
        self.init_net()
        self.init_gpio()
        self.init_settings()

    def init_net(self):
        # 创建网络
        try:
            print(sys.argv)
            self.net = jetson.inference.imageNet(
                "resnet18",
                [
                    "--model=/home/hgg/jetson-inference/python/training/classification/models/trash/resnet18.onnx", 
                    "--input_blob=input_0",
                    "--output_blob=output_0",
                    "--labels=/home/hgg/jetson-inference/python/training/classification/data/trash/label.txt"
                ]
            )
            print("Net create done...")
        except Exception as e:
            print("Net create err: %s" % (str(e)))

    def init_gpio(self):
        """
        初始化GPIO引脚
        """
        try:
            pin_out_list = [pin_food, pin_residual, pin_hazardous, pin_residual]
            GPIO.setmode(GPIO.BOARD)  # BOARD pin-numbering scheme
            GPIO.setup(pin_out_list, GPIO.OUT)
            GPIO.setup(pin_sensor, GPIO.IN)
            # GPIO输出引脚全部置低电平
            for pin_out in pin_out_list:
                GPIO.output(pin_out, GPIO.LOW)
            print("GPIO init done...")
        except Exception as e:
            print("GPIO init err: %s" % (str(e)))

    def init_settings(self):
        # 初始化设置
        try:
            res = requests.get(host_url, data="rKkwZHirl27G3XxrP62_s")
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

    def create_camera(self):
        """'
        Create the Camera instance
        """
        try:
            self.camera = jetson.utils.videoSource("/dev/video0")
        except Exception as e:
            print("Camera create err: %s" % (str(e)))

    def capture(self):
        """'
        拍照，识别并上传
        """
        img = self.camera.Capture()
        class_id, accuracy = self.net.Classify(img)
        # 提交数据
        post_data(class_id, accuracy)
        # 修改当前容量
        self.data["data"]["curCapacitity"] += 1
        self.data["data"]["capacityRate"] = (
            self.data["data"]["curCapacitity"] / self.data["data"]["totalCapacity"]
        )
        open_lid(class_id)

    def destroy_camera(self):
        del self.camera

    def err(self):
        pass

    def silence(self):
        pass

    def run(self):
        """
        jetson主进程,
        输入: 当前的红外传感器值
        """
        while True:
            self.handle_input()
            # 获取传感器最新的输入
            input = GPIO.input(pin_sensor)
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
    jetson_client().start()
    while True:
        pass
