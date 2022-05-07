import json
import jetson.inference, jetson.utils
from enum import Enum
import RPi.GPIO as GPIO
import time, requests, datetime

host_url = "http://192.168.137.1:3001/settings"
position = "rKkwZHirl27G3XxrP62_s"
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
        print("Data submit done...")
    else:
        print("Data submit err...")


def gpio_init():
    """
    初始化GPIO引脚
    """
    pin_out_list = [pin_food, pin_residual, pin_hazardous, pin_residual]
    GPIO.setmode(GPIO.BOARD)  # BOARD pin-numbering scheme
    GPIO.setup(pin_out_list, GPIO.OUT)
    GPIO.setup(pin_sensor, GPIO.IN)
    # GPIO输出引脚全部置低电平
    for pin_out in pin_out_list:
        GPIO.output(pin_out, GPIO.LOW)


def open_lid(lid):
    """
    选择一个垃圾盖子打开
    """
    GPIO.output(lid, GPIO.HIGH)
    time.sleep(10)
    GPIO.output(lid, GPIO.LOW)


class jetson_client:
    def __init__(self) -> None:
        # 设置初始状态
        self.state = jetson_state.IDEL

        # 创建网络
        try:
            self.net = jetson.inference.imageNet("googlenet")
        except Exception as e:
            print(str(e))

        # 初始化jetson 参数
        res = requests.get(host_url, data="rKkwZHirl27G3XxrP62_s")
        res = json.loads(res.text)
        self.data = res
        print('Jetson data init done...') 
        
        gpio_init()  # 初始化GPIO引脚
        print("GPIO init done...")

    def main_task(self):
        """
        jetson主进程,
        输入: 当前的红外传感器值
        """
        while True:

            # 获取传感器最新的输入
            input = GPIO.input(pin_sensor)

            if self.state is jetson_state.IDEL:
                if input is GPIO.HIGH:
                    self.state = jetson_state.WAKEUP

            elif self.state is jetson_state.WAKEUP:
                # Create the Camera instance
                self.camera = jetson.utils.videoSource("/dev/video0")
                self.state = jetson_state.WORK

            elif self.state is jetson_state.WORK:
                if input is GPIO.LOW:
                    self.state = jetson_state.SLEEP
                else:
                    img = self.camera.Capture()
                    class_id, accuracy = self.net.Classify(img)
                    # 提交数据
                    post_data(class_id, accuracy)
                    # 修改当前容量
                    self.data['data']['curCapacitity'] += 1
                    self.data['data']['capacityRate'] = self.data['data']['curCapacitity'] / self.data['data']['totalCapacity']
                    open_lid(class_id)

            elif self.state is jetson_state.SLEEP:
                del self.camera
                self.state = jetson_state.IDEL

    def __del__(self):
        GPIO.cleanup()  # cleanup all GPIOs

test = jetson_client()