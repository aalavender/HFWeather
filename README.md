# HFWeather
利用京东万象上的免费天气数据制作的HomeAssistant天气预报组件，天气/空气质量/生活指数数据一并存储，没有多余的Sensor。

数据源地址： https://way.jd.com/he/freeweather?city=beijing&appkey=您申请的APPKEY *（限5000次/天）* [获取KEY](https://uc.jdcloud.com/login?returnUrl=https%3A%2F%2Fwx.jdcloud.com%2Fmarket%2Fapi%2F10610)

# 安装
放入 <config directory>/custom_components/hfweather/ 目录

# 配置
**Example configuration.yaml:**
```yaml

```

**Configuration variables:**


### 程序说明（写给自己看的，请绕道）
天气插件获取的数据分为 *基础数据* 和 *进阶数据* 
* 基础数据，能满足lovelace界面中Weather Forecast Card的需求，具体数据项可以参考[官网](https://github.com/home-assistant/home-assistant/blob/dev/homeassistant/components/weather/__init__.py)
    1) temperature 当前温度
    2) temperature_unit 当前温度的单位（摄氏度和华氏度）
    3) pressure 大气压强
    4) humidity 空气湿度
    5) wind_speed 风速（公里/小时）
    6) wind_bearing 风向
    7) ozone 臭氧浓度
    8) attribution 版权归属信息
    9) visibility 能见度（公里）
    10) forecast 预报七天的数据（字典数组）
    11) precision 数据精度（已实现，默认0.1）
    12) state_attributes 相关属性值（已实现将基础数据全部放入属性）
    13) state 当前天气状态（已实现，返回condition）
    14) condition 当前天气状态
* 进阶数据，包括日出日落/月升月落/空气质量/小时预报和生活建议等数据，主要看得看数据源
