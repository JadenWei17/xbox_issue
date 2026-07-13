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

### 版本 / Version
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

### 版本 / Version
1.0

## 7 月 13 日 / July 13

### 做了什么 / What Was Done

- 完成 MPU6500 惯性测量单元的功能验证，确认传感器能够正常读取加速度和角速度数据，为后续获取小车的运动状态与姿态信息提供基础。
  Completed the functional verification of the MPU6500 inertial measurement unit, confirming that acceleration and angular-velocity data could be read correctly and providing a foundation for obtaining the car's motion and orientation information.
- 完成霍尔编码器的功能验证和信号消抖处理，减少机械抖动或信号波动引起的重复计数，提高车轮脉冲计数与行驶距离计算的稳定性。
  Completed the functional verification and signal debouncing of the Hall encoders, reducing duplicate counts caused by mechanical bounce or signal fluctuations and improving the stability of wheel-pulse counting and travel-distance calculations.
- 删除 Xbox 手柄左摇杆按键的读取与传输逻辑。由于后续控制流程未使用该按键，移除相关代码以简化输入处理和通信内容。
  Removed the reading and transmission logic for the Xbox controller's left-stick button. Because this button was not used in the subsequent control flow, the related code was removed to simplify input processing and communication.
- 完成第二种小车控制方式：通过键盘输入行驶方向、速度和目标距离，使小车按照指定参数移动，并在到达目标距离后停止。目前该模式仅支持向前和向后行驶，暂不支持左右转向。
  Completed a second control method for the car: the user enters the travel direction, speed, and target distance through the keyboard, allowing the car to move according to the specified parameters and stop after reaching the target distance. This mode currently supports only forward and backward movement; left and right turns are not yet supported.
- 在车头安装并接入超声波传感器，通过持续检测前方障碍物的距离，在小车向前行驶且检测到障碍物时触发主动急停，从而降低碰撞风险并提高行驶安全性。
  Installed and integrated an ultrasonic sensor at the front of the car. By continuously measuring the distance to obstacles ahead, the system triggers an active emergency stop when an obstacle is detected during forward movement, reducing collision risk and improving operational safety.

### 问题与计划 / Issues and Plans

- 获取并传输摄像头视频流，为后续实现远程画面监控、环境观察及视觉功能提供数据来源。
  Acquire and transmit the camera video stream to provide a data source for remote monitoring, environmental observation, and future vision-based functions.
- 规范小车各控制模块之间的通信协议，统一消息格式、命令类型、数据字段和异常处理方式，以提高通信的可读性、兼容性与可靠性。
  Standardize the communication protocol among the car's control modules by unifying message formats, command types, data fields, and error-handling methods to improve readability, compatibility, and reliability.
- 设计并实现通信建立过程中的三次握手机制，用于确认通信双方均已就绪，并降低连接状态不同步或无效指令传输的风险。
  Design and implement a three-way handshake for connection establishment to confirm that both communicating parties are ready and reduce the risk of unsynchronized connection states or invalid command transmission.

### 版本 / Version
1.1
