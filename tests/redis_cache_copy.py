#!/usr/bin/env python3
"""
Redis缓存复制工具
从源Redis数据库读取缓存，复制到目标Redis数据库
"""

import redis
from typing import Optional, Dict, Any
import time
from tqdm import tqdm


# ==================== 配置区域 ====================
# 请在此处填写源Redis和目标Redis的连接配置

# 源Redis配置
SOURCE_REDIS_CONFIG = {
    'host': 'localhost',        # 源Redis主机地址
    'port': 6379,               # 源Redis端口
    'password': 'tradingagents123',           # 源Redis密码，如果没有密码则填写None
    'db': 0,                    # 源Redis数据库编号
    'decode_responses': True    # 是否自动解码响应（建议True）
}

# 目标Redis配置
TARGET_REDIS_CONFIG = {
    'host': '36.213.71.200',        # 目标Redis主机地址
    'port': 30009,               # 目标Redis端口
    'password': 'E1SkG0PaDMEPTAxY',           # 目标Redis密码，如果没有密码则填写None
    'db': 10,                    # 目标Redis数据库编号
    'decode_responses': True    # 是否自动解码响应（建议True）
}

# 复制选项
COPY_OPTIONS = {
    'pattern': '*',             # 键匹配模式，'*'表示所有键
    'batch_size': 1000,         # 批量处理键的数量
    'overwrite': True,          # 是否覆盖目标数据库中已存在的键
    'ttl_preserve': True,       # 是否保留TTL（过期时间）
    'verify': True              # 复制后是否验证数据一致性
}
# ==================== 配置区域结束 ====================


class RedisCacheCopier:
    """Redis缓存复制器"""
    
    def __init__(self, source_config: Dict[str, Any], target_config: Dict[str, Any], 
                 copy_options: Dict[str, Any]):
        """
        初始化Redis缓存复制器
        
        Args:
            source_config: 源Redis配置
            target_config: 目标Redis配置
            copy_options: 复制选项
        """
        self.source_config = source_config
        self.target_config = target_config
        self.copy_options = copy_options
        
        self.source_client: Optional[redis.Redis] = None
        self.target_client: Optional[redis.Redis] = None
        
    def connect(self) -> bool:
        """连接源和目标Redis服务器"""
        try:
            # 连接源Redis
            print(f"正在连接源Redis: {self.source_config['host']}:{self.source_config['port']}...")
            self.source_client = redis.Redis(
                host=self.source_config['host'],
                port=self.source_config['port'],
                password=self.source_config['password'],
                db=self.source_config['db'],
                decode_responses=self.source_config['decode_responses'],
                socket_timeout=10,
                socket_connect_timeout=10
            )
            self.source_client.ping()
            print(f"✅ 源Redis连接成功")
            
            # 连接目标Redis
            print(f"正在连接目标Redis: {self.target_config['host']}:{self.target_config['port']}...")
            self.target_client = redis.Redis(
                host=self.target_config['host'],
                port=self.target_config['port'],
                password=self.target_config['password'],
                db=self.target_config['db'],
                decode_responses=self.target_config['decode_responses'],
                socket_timeout=10,
                socket_connect_timeout=10
            )
            self.target_client.ping()
            print(f"✅ 目标Redis连接成功")
            
            return True
            
        except redis.ConnectionError as e:
            print(f"❌ Redis连接失败: {e}")
            return False
        except redis.AuthenticationError as e:
            print(f"❌ Redis认证失败: {e}")
            return False
        except Exception as e:
            print(f"❌ 连接出错: {e}")
            return False
    
    def get_all_keys(self) -> list:
        """获取所有匹配模式的键"""
        pattern = self.copy_options['pattern']
        print(f"正在扫描键（模式: {pattern}）...")
        
        keys = []
        cursor = 0
        
        while True:
            cursor, batch_keys = self.source_client.scan(
                cursor=cursor,
                match=pattern,
                count=self.copy_options['batch_size']
            )
            keys.extend(batch_keys)
            
            if cursor == 0:
                break
        
        print(f"找到 {len(keys)} 个键")
        return keys
    
    def copy_key(self, key: str) -> bool:
        """
        复制单个键及其数据
        
        Args:
            key: 要复制的键名
            
        Returns:
            是否复制成功
        """
        try:
            # 检查目标键是否存在
            if not self.copy_options['overwrite'] and self.target_client.exists(key):
                return True  # 跳过已存在的键
            
            # 获取键的类型
            key_type_raw = self.source_client.type(key)
            key_type = key_type_raw.decode() if isinstance(key_type_raw, bytes) else key_type_raw
            
            # 获取TTL
            ttl = self.source_client.ttl(key)
            if ttl == -1:
                ttl = None  # 永不过期
            elif ttl == -2:
                return False  # 键不存在
            
            # 根据类型复制数据
            if key_type == 'string':
                value = self.source_client.get(key)
                if value is not None:
                    self.target_client.set(key, value, ex=ttl if self.copy_options['ttl_preserve'] and ttl else None)
                    
            elif key_type == 'hash':
                hash_data = self.source_client.hgetall(key)
                if hash_data:
                    self.target_client.hset(key, mapping=hash_data)
                    if self.copy_options['ttl_preserve'] and ttl:
                        self.target_client.expire(key, ttl)
                        
            elif key_type == 'list':
                list_data = self.source_client.lrange(key, 0, -1)
                if list_data:
                    self.target_client.delete(key)  # 先删除目标键
                    if list_data:
                        self.target_client.rpush(key, *list_data)
                    if self.copy_options['ttl_preserve'] and ttl:
                        self.target_client.expire(key, ttl)
                        
            elif key_type == 'set':
                set_data = self.source_client.smembers(key)
                if set_data:
                    self.target_client.delete(key)  # 先删除目标键
                    if set_data:
                        self.target_client.sadd(key, *set_data)
                    if self.copy_options['ttl_preserve'] and ttl:
                        self.target_client.expire(key, ttl)
                        
            elif key_type == 'zset':
                zset_data = self.source_client.zrange(key, 0, -1, withscores=True)
                if zset_data:
                    self.target_client.delete(key)  # 先删除目标键
                    if zset_data:
                        # zset_data是元组列表 [(member, score), ...]
                        pipe = self.target_client.pipeline()
                        for member, score in zset_data:
                            pipe.zadd(key, {member: score})
                        pipe.execute()
                    if self.copy_options['ttl_preserve'] and ttl:
                        self.target_client.expire(key, ttl)
                        
            else:
                print(f"⚠️  未支持的数据类型: {key_type} (键: {key})")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ 复制键 '{key}' 时出错: {e}")
            return False
    
    def verify_key(self, key: str) -> bool:
        """
        验证键是否复制成功
        
        Args:
            key: 要验证的键名
            
        Returns:
            是否验证通过
        """
        try:
            source_type_raw = self.source_client.type(key)
            target_type_raw = self.target_client.type(key)
            
            source_type_str = source_type_raw.decode() if isinstance(source_type_raw, bytes) else source_type_raw
            target_type_str = target_type_raw.decode() if isinstance(target_type_raw, bytes) else target_type_raw
            
            if source_type_str != target_type_str:
                return False
            
            if source_type_str == 'string':
                return self.source_client.get(key) == self.target_client.get(key)
            elif source_type_str == 'hash':
                return self.source_client.hgetall(key) == self.target_client.hgetall(key)
            elif source_type_str == 'list':
                return self.source_client.lrange(key, 0, -1) == self.target_client.lrange(key, 0, -1)
            elif source_type_str == 'set':
                return self.source_client.smembers(key) == self.target_client.smembers(key)
            elif source_type_str == 'zset':
                return self.source_client.zrange(key, 0, -1, withscores=True) == self.target_client.zrange(key, 0, -1, withscores=True)
            
            return True
            
        except Exception as e:
            print(f"❌ 验证键 '{key}' 时出错: {e}")
            return False
    
    def copy_all(self) -> Dict[str, Any]:
        """
        复制所有匹配的键
        
        Returns:
            复制结果统计
        """
        if not self.source_client or not self.target_client:
            print("❌ 请先连接Redis服务器")
            return {}
        
        # 获取所有键
        keys = self.get_all_keys()
        
        if not keys:
            print("⚠️  没有找到要复制的键")
            return {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}
        
        # 统计信息
        stats = {
            'total': len(keys),
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'failed_keys': []
        }
        
        print(f"\n开始复制 {len(keys)} 个键...")
        start_time = time.time()
        
        # 使用进度条
        with tqdm(total=len(keys), desc="复制进度", unit="键") as pbar:
            for key in keys:
                # 检查是否已存在且不覆盖
                if not self.copy_options['overwrite'] and self.target_client.exists(key):
                    stats['skipped'] += 1
                    pbar.update(1)
                    continue
                
                if self.copy_key(key):
                    # 验证（如果启用）
                    if self.copy_options['verify']:
                        if self.verify_key(key):
                            stats['success'] += 1
                        else:
                            stats['failed'] += 1
                            stats['failed_keys'].append(key)
                    else:
                        stats['success'] += 1
                else:
                    stats['failed'] += 1
                    stats['failed_keys'].append(key)
                
                pbar.update(1)
        
        elapsed_time = time.time() - start_time
        
        # 打印统计信息
        print(f"\n{'='*60}")
        print(f"复制完成！")
        print(f"{'='*60}")
        print(f"总键数:     {stats['total']}")
        print(f"成功:       {stats['success']}")
        print(f"失败:       {stats['failed']}")
        print(f"跳过:       {stats['skipped']}")
        print(f"耗时:       {elapsed_time:.2f} 秒")
        
        if stats['failed_keys']:
            print(f"\n失败的键 ({len(stats['failed_keys'])} 个):")
            for key in stats['failed_keys'][:10]:  # 只显示前10个
                print(f"  - {key}")
            if len(stats['failed_keys']) > 10:
                print(f"  ... 还有 {len(stats['failed_keys']) - 10} 个失败的键")
        
        return stats
    
    def close(self):
        """关闭Redis连接"""
        if self.source_client:
            self.source_client.close()
        if self.target_client:
            self.target_client.close()
        print("\n连接已关闭")


def main():
    """主函数"""
    print("="*60)
    print("Redis缓存复制工具")
    print("="*60)
    print()
    
    # 创建复制器
    copier = RedisCacheCopier(
        source_config=SOURCE_REDIS_CONFIG,
        target_config=TARGET_REDIS_CONFIG,
        copy_options=COPY_OPTIONS
    )
    
    try:
        # 连接Redis
        if not copier.connect():
            print("❌ 无法连接到Redis服务器，请检查配置")
            return
        
        # 显示配置信息
        print(f"\n复制配置:")
        print(f"  模式: {COPY_OPTIONS['pattern']}")
        print(f"  覆盖已存在键: {COPY_OPTIONS['overwrite']}")
        print(f"  保留TTL: {COPY_OPTIONS['ttl_preserve']}")
        print(f"  验证数据: {COPY_OPTIONS['verify']}")
        print()
        
        # 确认操作
        response = input("确认开始复制？(y/n): ").strip().lower()
        if response != 'y':
            print("操作已取消")
            return
        
        # 执行复制
        stats = copier.copy_all()
        
        if stats.get('success', 0) > 0:
            print(f"\n✅ 复制成功完成！")
        else:
            print(f"\n⚠️  没有成功复制任何键")
            
    except KeyboardInterrupt:
        print("\n\n操作被用户中断")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        copier.close()


if __name__ == '__main__':
    main()

