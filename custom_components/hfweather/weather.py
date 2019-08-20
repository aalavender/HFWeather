#from datetime import datetime, timedelta

#https://github.com/home-assistant/home-assistant/blob/dev/homeassistant/components/weather/__init__.py
from homeassistant.components.weather import (
    WeatherEntity, ATTR_FORECAST_CONDITION, ATTR_FORECAST_PRECIPITATION,
    ATTR_FORECAST_TEMP, ATTR_FORECAST_TEMP_LOW, ATTR_FORECAST_TIME, ATTR_FORECAST_WIND_BEARING,
    ATTR_FORECAST_WIND_SPEED)

#https://github.com/home-assistant/home-assistant/blob/dev/homeassistant/const.py
from homeassistant.const import (TEMP_CELSIUS, TEMP_FAHRENHEIT, CONF_API_KEY, CONF_REGION, CONF_NAME)

import requests
import json
import logging
import asyncio

VERSION = '0.1.0'
DOMAIN = 'hfweather'

ATTR_AQI = "aqi"
ATTR_HOURLY_FORECAST = "hourly_forecast"
ATTR_SUGGESTION = "suggestion"
ATTR_PRECIPITATION_PROBABILITY = "precipitation_probability"
ATTR_UPDATE_TIME = "update_time"
ATTR_CONDITION_CN = "condition_cn"
ATTR_CUSTOM_UI_MORE_INFO = "custom_ui_more_info"

# mapping status, why? because
# https://github.com/home-assistant/home-assistant-polymer/blob/master/src/cards/ha-weather-card.js#L279
# https://open.caiyunapp.com/%E5%BD%A9%E4%BA%91%E5%A4%A9%E6%B0%94_API/v2.5

# mapping state, why? because
# https://github.com/home-assistant/home-assistant-polymer/blob/master/src/cards/ha-weather-card.js#L279
# https://dev.heweather.com/docs/refer/condition
# 和风天气少一个clear-night状态(及一个晴朗的月亮)，其他的状态远远超过HA
CONDITION_MAP = {
    '100': 'sunny', #晴  Sunny/Clear
    '101': 'partlycloudy',  #多云
    '102': 'partlycloudy',  #少云
    '103': 'partlycloudy',  #晴间多云
    '104': 'cloudy',    #阴

    '200': 'windy', #有风
    '201': 'windy', #平静
    '202': 'windy', #微风
    '203': 'windy', #和风  	Moderate/Gentle Breeze
    '204': 'windy', #清风
    '205': 'windy-variant', #强风/劲风
    '206': 'windy-variant', #疾风
    '207': 'windy-variant', #大风
    '208': 'windy-variant', #烈风
    '209': 'hail',  #风暴
    '210': 'hail',  #狂爆风
    '211': 'hail',  #飓风
    '212': 'hail',  #龙卷风
    '213': 'hail',  #热带风暴

    '300': 'rainy',  #阵雨
    '301': 'rainy',  #强阵雨
    '302': 'lightning-rainy',  # 雷阵雨
    '303': 'lightning-rainy',  # 强雷阵雨
    '304': 'hail',  # 雷阵雨伴有冰雹
    '305': 'rainy',  # 小雨
    '306': 'rainy',  # 中雨
    '307': 'rainy',     # 大雨
    '308': 'hail',     #极端降雨
    '309': 'rainy',    #毛毛雨/细雨
    '310': 'pouring',  #暴雨
    '311': 'pouring',  #大暴雨
    '312': 'pouring',  #特大暴雨
    '313': 'hail',  #冻雨
    '314': 'rainy',  # 小到中雨
    '315': 'rainy',  # 中到大雨
    '316': 'pouring',  #大到暴雨
    '317': 'pouring',  #暴雨到大暴雨
    '318': 'pouring',  #大暴雨到特大暴雨
    '399': 'rainy',  #大暴雨到特大暴雨

    '400': 'snowy',  #小雪
    '401': 'snowy',  #中雪
    '402': 'snowy',  #大雪
    '403': 'snowy',  #暴雪
    '404': 'snowy-rainy',  #雨夹雪
    '405': 'snowy-rainy',  #雨雪天气
    '406': 'snowy-rainy',  #阵雨夹雪
    '407': 'snowy',  # 阵雪
    '408': 'snowy',  # 小到中雪
    '409': 'snowy',  # 中到大雪
    '410': 'snowy',  # 大到暴雪
    '499': 'snowy',  # 雪

    '500': 'fog',  # 薄雾
    '501': 'fog',  # 雾
    '502': 'fog',  # 霾
    '503': 'fog',  # 扬沙
    '504': 'fog',  # 浮尘
    '507': 'hail',  # 沙尘暴
    '508': 'hail',  # 强沙尘暴
    '509': 'fog',  # 浓雾
    '510': 'fog',  # 强浓雾
    '511': 'fog',  # 中度霾
    '512': 'fog',  # 重度霾
    '513': 'hail',  # 严重霾
}

SUGGESTION_MAP = {
    'air': '空气',
    'drsg': '穿衣',
    'uv': '紫外',
    'comf': '体感',
    'flu': '感冒',
    'sport': '运动',
    'trav': '旅游',
    'cw': '洗车'
}

_LOGGER = logging.getLogger(__name__)


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    _LOGGER.info("async_setup_platform sensor HFWeather")
    async_add_devices([HFWeather(api_key=config.get(CONF_API_KEY),
                            region=config.get(CONF_REGION, 'CN101210201'),  #默认为湖州
                            name=config.get(CONF_NAME, '天气助手'))], True)


class HFWeather(WeatherEntity):
    """Representation of a weather condition."""

    def __init__(self, api_key: str, region: str, name: str):
        self._api_key = api_key
        self._region = region
        self._name = name
        self._msg = "初始化"
        self._data_source_update = None # 数据源更新时间
        self._now_weather_data = None   # 存储实况天气数据
        self._now_air_data = None       # 存储实况空气质量数据
        self._now_life_data = None      # 存储实况生活指数数据
        self._daily_forecast_data = None    # 存储天气预报数据（每天）
        self._hourly_forecast_data = None   # 存储天气预报数据（每小时）

    @property
    def name(self):
        return self._name

    @property
    def condition(self):
        """Return the weather condition."""
        if self._now_weather_data:
            return CONDITION_MAP[self._now_weather_data["cond"]["code"]]
        else:
            return self._msg

    @property
    def condition_cn(self):
        """Return the weather condition by txt"""
        if self._now_weather_data:
            return self._now_weather_data["cond"]["txt"]
        else:
            return self._msg
    @property
    def temperature(self):
        if self._now_weather_data:
            return float(self._now_weather_data['tmp'])
        else:
            return self._msg

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def pressure(self):
        """大气压强"""
        if self._now_weather_data:
            return float(self._now_weather_data['pres'])
        else:
            return self._msg

    @property
    def humidity(self):
        if self._now_weather_data:
            return float(self._now_weather_data['hum'])
        else:
            return self._msg

    @property
    def wind_speed(self):
        """风速"""
        if self._now_weather_data:
            return float(self._now_weather_data["wind"]["spd"])
        else:
            return self._msg

    @property
    def wind_bearing(self):
        """风向"""
        if self._now_weather_data:
            return float(self._now_weather_data["wind"]["deg"])
        else:
            return self._msg

    @property
    def ozone(self):
        """臭氧浓度"""
        if self._now_air_data:
            return self._now_air_data['o3']
        else:
            return self._msg

    @property
    def attribution(self):
        """Return the attribution."""
        return '和风天气提供数据源'

    @property
    def visibility(self):
        """能见度"""
        if self._now_weather_data:
            return self._now_weather_data['vis']
        else:
            return self._msg

    @property
    def state_attributes(self):
        data = super(HFWeather, self).state_attributes
        data[ATTR_SUGGESTION] = self.suggestion
        data[ATTR_AQI] = self.aqi
        data[ATTR_HOURLY_FORECAST] = self.hourly_forecast
        data[ATTR_UPDATE_TIME] = self.update_time
        data[ATTR_CONDITION_CN] = self.condition_cn
        data[ATTR_CUSTOM_UI_MORE_INFO] = "hf_weather-more-info"
        return data

    @property
    def forecast(self):
        """天为单位的预报"""
        forecast_data = []
        if self._daily_forecast_data:
            for i in range(len(self._daily_forecast_data)):
                data_dict = {
                    ATTR_FORECAST_TIME: self._daily_forecast_data[i]["date"],
                    ATTR_FORECAST_CONDITION: CONDITION_MAP[self._daily_forecast_data[i]["cond"]["code_d"]],
                    ATTR_FORECAST_PRECIPITATION: float(self._daily_forecast_data[i]["pcpn"]),  #降水量
                    ATTR_PRECIPITATION_PROBABILITY: float(self._daily_forecast_data[i]["pop"]),  # 降水概率
                    ATTR_FORECAST_TEMP: float(self._daily_forecast_data[i]['tmp']['max']),
                    ATTR_FORECAST_TEMP_LOW: float(self._daily_forecast_data[i]['tmp']['min'])
                }
                forecast_data.append(data_dict)

        return forecast_data

    # =======================================
    # 以下属性基类中不涉及，属于自定义数据
    # =======================================
    @property
    def suggestion(self):
        """生活建议，返回字典数组"""
        if self._now_life_data:
            return [{'title': k, 'title_cn': SUGGESTION_MAP.get(k,k), 'brf': v.get('brf'),
                                    'txt': v.get('txt') } for k, v in self._now_life_data.items()]
        else:
            return self._msg

    @property
    def aqi(self):
        """AQI（国标）"""
        if self._now_air_data:
            return self._now_air_data
        else:
            return self._msg

    @property
    def update_time(self):
        """数据源更新时间."""
        if self._data_source_update:
            return self._data_source_update
        else:
            return self._msg
    @property
    def hourly_forecast(self):
        """小时为单位的预报"""
        forecast_data = []
        if self._hourly_forecast_data:
            for i in range(len(self._hourly_forecast_data)):
                data_dict = {
                    ATTR_FORECAST_TIME: self._hourly_forecast_data[i]["date"],
                    ATTR_FORECAST_CONDITION: CONDITION_MAP[self._hourly_forecast_data[i]["cond"]["code"]],
                    ATTR_PRECIPITATION_PROBABILITY: float(self._hourly_forecast_data[i]["pop"]),  # 降水概率
                    ATTR_FORECAST_TEMP: float(self._hourly_forecast_data[i]['tmp'])
                }
                forecast_data.append(data_dict)

        return forecast_data

    def update(self):
        _LOGGER.info("HFWeather updating from  https://way.jd.com/he/freeweather")

        json_text = requests.get(
            str.format("https://way.jd.com/he/freeweather?city={}&appkey={}", self._region,
                       self._api_key)).content
        json_data = json.loads(json_text)
        self._msg = json_data["msg"]    # 查询结果说明

        if self._msg == "查询成功":
            self._data_source_update = json_data["result"]["HeWeather5"][0]["basic"]["update"]["loc"]  # 数据源更新时间

            self._now_weather_data = json_data["result"]["HeWeather5"][0]["now"]
            self._now_air_data = json_data["result"]["HeWeather5"][0]["aqi"]["city"]
            self._now_life_data = json_data["result"]["HeWeather5"][0]["suggestion"]

            self._daily_forecast_data = json_data["result"]["HeWeather5"][0]["daily_forecast"]
            self._hourly_forecast_data = json_data["result"]["HeWeather5"][0]["hourly_forecast"]

