from asyncio.windows_events import NULL
import nanocamera as nano
import RPi.GPIO as GPIO
import time
import web
import requests
from enum import Enum
import datetime


class jetson_state(Enum):
    IDEL = 1     # 空闲状态
    WAKEUP = 2     # 摄像头开启
    SLEEP = 3     # 摄像头关闭
    WORK = 4     # 拍照，识别，上传


# 引脚定义
pin_food = 1
pin_residual = 2
pin_hazardous = 3
pin_recycle = 4
pin_sensor = 5

type_list = ['food', 'residual', 'hazardous', 'recycle', 'sensor']

post_url = 'http://192.168.137.1:3001/jetson'
position = 'rKkwZHirl27G3XxrP62_s'

urls = ('/(.*)', 'index')


def gpio_init():
    '''
    初始化GPIO引脚
    '''
    pin_out_list = [pin_food, pin_residual, pin_hazardous, pin_residual]
    GPIO.setmode(GPIO.BOARD)  # BOARD pin-numbering scheme
    GPIO.setup(pin_out_list, GPIO.OUT)
    GPIO.setup(pin_sensor, GPIO.IN)
    # GPIO输出引脚全部置低电平
    for pin in pin_out_list:
        GPIO.output(pin, GPIO.LOW)


def classify_img(img):
    '''
    分类函数
    '''
    return [pin_food, 0.8]


def get_curtime():
    '''
    获取当前时间
    '''
    cur_time = datetime.datetime.now()
    time_str = datetime.datetime.strftime(cur_time, '%Y-%m-%d %H:%M:%S')
    return time_str


def post_data(type, accuracy):
    '''
    发送数据
    '''
    r = requests.post(
        url = post_url,
        data = {
            time: get_curtime(),
            position: position,
            type: type_list[type],
            accuracy: accuracy,
        })

    if r.status_code is 200:
        print('Data submit done...')
    else:
        print('Data submit err...')


class index():
    '''
    处理主机post请求
    '''

    def POST(self, data):
        '''
        post修改jetson设置
        '''
        if client is not NULL:
            for key, value in data:
                client[key] = value


class jetson_client:
    def __init__(self) -> None:
        # 设置初始状态
        self.state = jetson_state.IDEL

        # 初始化jetson 参数
        self.capacityRate = 0.0
        self.totalCapacity = 10
        self.curCapacitity = 0
        self.closeOnFull = False
        self.alertOnFull = False,
        self.residual = True,
        self.hazardous = True,
        self.food = True,
        self.recyclable = True

        gpio_init()  # 初始化GPIO引脚

    def main_task(self):
        '''
        jetson主进程, 
        输入: 当前的红外传感器值
        '''
        while True:

            # 获取传感器最新的输入
            input = GPIO.input(pin_sensor)

            if self.state is jetson_state.IDEL:
                if input is GPIO.HIGH:
                    self.state = jetson_state.WAKEUP

            elif self.state is jetson_state.WAKEUP:
                # Create the Camera instance
                self.camera = nano.Camera(
                    flip=0, width=640, height=480, fps=30)
                if self.camera.isReady():
                    print('Camera is ready...')
                    self.state = jetson_state.WORK
                else:
                    print('Camera error: ', self.camera.hasError())

            elif self.state is jetson_state.WORK:
                if input is GPIO.LOW:
                    self.state = jetson_state.SLEEP
                else:
                    img = self.camera.read()
                    [ret, accuracy] = classify_img(img)
                    post_data(ret, accuracy)
                    GPIO.output(ret, GPIO.HIGH)
                    time.sleep(10)
                    GPIO.output(ret, GPIO.LOW)

            elif self.state is jetson_state.SLEEP:
                self.camera.release()
                self.state = jetson_state.IDEL

    def __del__(self):
        GPIO.cleanup()  # cleanup all GPIOs


if __name__ == "__main__":
    client = jetson_client()
    app = application(urls, globals())
    app.add_process(client.main_task)
    app.run()
