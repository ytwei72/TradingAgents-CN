"""
MQTT 消息引擎实现
"""

import json
import time
from typing import Dict, Any, Callable, Optional
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    mqtt = None

from tradingagents.utils.logging_manager import get_logger
from .base import MessageEngine

logger = get_logger('messaging.mqtt')


class MQTTEngine(MessageEngine):
    """MQTT 消息引擎实现"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化MQTT引擎
        
        Args:
            config: 配置字典，包含：
                - host: MQTT服务器地址
                - port: 端口（默认1883）
                - username: 用户名（可选）
                - password: 密码（可选）
                - client_id: 客户端ID（默认'tradingagents'）
                - clean_session: 是否清理会话（默认True）
                - keepalive: 保活时间（默认60秒）
        """
        if not MQTT_AVAILABLE:
            raise ImportError("paho-mqtt 未安装，请运行: pip install paho-mqtt")
        
        self.config = config
        self.client: Optional[mqtt.Client] = None
        self.callbacks: Dict[str, Callable] = {}
        self._connected = False
        
    def connect(self) -> bool:
        """连接MQTT服务器"""
        try:
            self.client = mqtt.Client(
                client_id=self.config.get('client_id', 'tradingagents'),
                clean_session=self.config.get('clean_session', True)
            )
            
            if self.config.get('username'):
                self.client.username_pw_set(
                    self.config['username'],
                    self.config.get('password')
                )
            
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect
            
            self.client.connect(
                self.config['host'],
                self.config.get('port', 1883),
                self.config.get('keepalive', 60)
            )
            
            self.client.loop_start()
            
            # 等待连接完成
            timeout = 5
            start_time = time.time()
            while not self._connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if self._connected:
                logger.info(f"MQTT连接成功: {self.config['host']}:{self.config.get('port', 1883)}")
                return True
            else:
                logger.error("MQTT连接超时")
                return False
                
        except Exception as e:
            logger.error(f"MQTT连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
                self._connected = False
                logger.info("MQTT连接已断开")
            except Exception as e:
                logger.error(f"MQTT断开连接失败: {e}")
    
    def publish(self, topic: str, message: Dict[str, Any]) -> bool:
        """发布消息"""
        if not self.is_connected():
            logger.warning("MQTT未连接，无法发布消息")
            return False
        
        try:
            payload = json.dumps(message, ensure_ascii=False)
            result = self.client.publish(topic, payload, qos=1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"MQTT消息已发布: {topic}")
                return True
            else:
                logger.error(f"MQTT发布失败: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"MQTT发布消息异常: {e}")
            return False
    
    def subscribe(self, topic: str, callback: Callable[[str, Dict[str, Any]], None]) -> bool:
        """订阅主题"""
        if not self.is_connected():
            logger.warning("MQTT未连接，无法订阅")
            return False
        
        try:
            self.callbacks[topic] = callback
            result = self.client.subscribe(topic, qos=1)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"MQTT已订阅主题: {topic}")
                return True
            else:
                logger.error(f"MQTT订阅失败: {result[0]}")
                return False
        except Exception as e:
            logger.error(f"MQTT订阅异常: {e}")
            return False
    
    def unsubscribe(self, topic: str) -> bool:
        """取消订阅"""
        if not self.is_connected():
            return False
        
        try:
            result = self.client.unsubscribe(topic)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                if topic in self.callbacks:
                    del self.callbacks[topic]
                logger.info(f"MQTT已取消订阅: {topic}")
                return True
            return False
        except Exception as e:
            logger.error(f"MQTT取消订阅异常: {e}")
            return False
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected and self.client is not None
    
    def _on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        if rc == 0:
            self._connected = True
            logger.info("MQTT客户端已连接")
        else:
            self._connected = False
            logger.error(f"MQTT连接失败，错误码: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """消息接收回调"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode('utf-8'))
            
            if topic in self.callbacks:
                self.callbacks[topic](topic, payload)
            else:
                logger.warning(f"收到未订阅主题的消息: {topic}")
        except Exception as e:
            logger.error(f"处理MQTT消息异常: {e}")
    
    def _on_disconnect(self, client, userdata, rc):
        """断开连接回调"""
        self._connected = False
        if rc != 0:
            logger.warning(f"MQTT意外断开连接，错误码: {rc}")
        else:
            logger.info("MQTT正常断开连接")

