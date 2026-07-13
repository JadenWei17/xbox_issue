# 工作日志 / Work Log

## 7 月 11 日 / July 11

### 做了什么 / What Was Done

- 完成使用 Xbox 手柄左摇杆控制小车移动的功能，完善 Windows 端 Xbox 手柄程序，加入摇杆死区处理。
  Completed the function of controlling the car's movement with the left joystick of the Xbox controller, improved the Windows-side Xbox controller program, and added joystick dead-zone processing.
- 完成树莓派端差速驱动混控逻辑，将手柄的前后、转向输入转换为左右轮速度，并增加轮速归一化、最大速度限制及左右轮独立校准缩放功能。
  Completed the differential-drive mixing logic on the Raspberry Pi, converting the controller's forward/backward and steering inputs into left and right wheel speeds, and added wheel-speed normalization, maximum speed limiting, and independent calibration scaling for the left and right wheels.
- 完成树莓派端 UDP 数据接收、输入平滑及 Arduino 串口指令发送流程。
  Completed the Raspberry Pi workflow for UDP data reception, input smoothing, and Arduino serial command transmission.
- 加入通信超时自动停车及运行状态统计输出。
  Added automatic stopping upon communication timeout and runtime status statistics output.
- 完成 Arduino Mega 电机控制程序，支持四电机方向与 PWM 控制、串口命令解析、急停锁定和 500 ms 看门狗自动停车。
  Completed the Arduino Mega motor control program, supporting direction and PWM control for four motors, serial command parsing, emergency-stop latching, and automatic stopping through a 500 ms watchdog.

### 问题与计划 / Issues and Plans

- 当天测试中发现各电机的安装顺序和转动方向尚未正确匹配，导致小车无法正常左右转向。
  During testing, it was found that the installation order and rotation directions of the motors had not been correctly matched, preventing the car from turning left and right normally.

### version 
0.0

## 7 月 12 日 / July 12

### 做了什么 / What Was Done

- 通过逐一确认并调整四个电机的顺序与转动方向，解决小车无法正常左右转向的问题。
  Solved the problem of the car being unable to turn left and right normally by checking and adjusting the order and rotation direction of each of the four motors.
- 支持通过 Y 键发送急停、X 键发送复位命令。急停命令从树莓派 GPIO17 到 Arduino Mega D18，实现硬件急停信号检测、急停锁定与复位。
  Added support for sending an emergency-stop command with the Y button and a reset command with the X button. The emergency-stop command is transmitted from Raspberry Pi GPIO17 to Arduino Mega D18, enabling hardware emergency-stop signal detection, emergency-stop latching, and reset.

### 问题与计划 / Issues and Plans

- 使用车轮上的霍尔传感器记录左右轮行驶距离，并结合两轮里程计算小车在空间中的位置。
  Use the Hall sensors on the wheels to record the travel distances of the left and right wheels, and calculate the car's spatial position based on the mileage of both wheels.
- 在小车车头加装超声波传感器，通过检测前方障碍物的距离实现第二种基于 ISR 的急停方式，防止小车撞墙，提高急停系统的可靠性和安全性。
  Install an ultrasonic sensor at the front of the car to implement a second ISR-based emergency-stop method by detecting the distance to obstacles ahead, preventing the car from hitting walls and improving the reliability and safety of the emergency-stop system.

### version 
1.0

## 7 月 13 日

### 做了什么 / What Was Done

- 完成mpu6500验证。
- 完成霍尔编码器验证与消抖。