#!/usr/bin/env python3
"""
A股上市公司字典表管理器
用于存储和查询A股上市公司的基础信息，减少对外部API的依赖

集合名称: stock_dict
数据库: tradingagents (MongoDB)

【使用方式】
1. 直接执行本文件进行建表和数据同步:
   python -m tradingagents.storage.mongodb.stock_dict_manager

2. 在代码中使用:
   from tradingagents.storage.mongodb.stock_dict_manager import stock_dict_manager
   info = stock_dict_manager.get_by_symbol("000001")

【定时更新方案（待实现）】
建议使用以下方式实现定时更新：
1. APScheduler定时任务: 在FastAPI应用中添加定时任务，每周末全量更新
2. Celery异步任务: 适合分布式部署，可设置定时Beat任务
3. 系统Cron: 通过crontab调用本脚本，如: 0 2 * * 0 python stock_dict_manager.py
4. 增量更新: 每日检测新上市/退市股票，仅更新变化部分

推荐更新频率：
- 全量更新: 每周1次（周末）
- 增量检测: 每日1次（交易日收盘后）
"""

import os
import sys
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd

from tradingagents.utils.logging_manager import get_logger
logger = get_logger('storage')

try:
    from pymongo import MongoClient, ASCENDING, DESCENDING
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    logger.warning("pymongo未安装，MongoDB功能不可用")

# 数据源可用性检查
try:
    import tushare as ts
    TUSHARE_AVAILABLE = True
except ImportError:
    TUSHARE_AVAILABLE = False

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False


class StockDictManager:
    """A股上市公司字典表管理器"""
    
    # 集合名称
    COLLECTION_NAME = "stock_dict"
    
    def __init__(self):
        self.collection = None
        self.connected = False
        
        if MONGODB_AVAILABLE:
            self._connect()
    
    def _connect(self):
        """连接到MongoDB"""
        try:
            from tradingagents.storage.manager import get_mongo_collection
            
            self.collection = get_mongo_collection(self.COLLECTION_NAME)
            if self.collection is None:
                logger.error("❌ 统一连接管理不可用，无法连接MongoDB")
                self.connected = False
                return
            
            # 创建索引
            self._create_indexes()
            
            self.connected = True
            logger.info(f"✅ MongoDB连接成功: {self.COLLECTION_NAME}")
            
        except Exception as e:
            logger.error(f"❌ MongoDB连接失败: {e}")
            self.connected = False
    
    def _create_indexes(self):
        """创建索引以提高查询性能"""
        try:
            # 主键索引：股票代码唯一
            self.collection.create_index("symbol", unique=True)
            
            # 复合索引：按交易所+市场查询
            self.collection.create_index([
                ("exchange", ASCENDING),
                ("market", ASCENDING)
            ])
            
            # 单字段索引
            self.collection.create_index("industry")
            self.collection.create_index("name")
            self.collection.create_index("list_status")
            self.collection.create_index([("updated_at", DESCENDING)])
            
            logger.info("✅ stock_dict索引创建成功")
            
        except Exception as e:
            logger.error(f"❌ stock_dict索引创建失败: {e}")
    
    # ==================== 数据同步方法 ====================
    
    def sync_from_tushare(self, token: str = None) -> int:
        """
        从Tushare同步A股上市公司数据
        
        Args:
            token: Tushare API token，如不提供则从环境变量获取
            
        Returns:
            int: 同步的记录数，失败返回-1
        """
        if not self.connected:
            logger.error("❌ MongoDB未连接")
            return -1
        
        if not TUSHARE_AVAILABLE:
            logger.error("❌ Tushare库未安装")
            return -1
        
        # 获取token
        if not token:
            token = os.getenv('TUSHARE_TOKEN', '')
        
        if not token:
            logger.error("❌ 未找到Tushare API token")
            return -1
        
        try:
            logger.info("🔄 从Tushare同步A股上市公司数据...")
            
            ts.set_token(token)
            pro = ts.pro_api()
            
            # 获取所有上市公司（包含上市和退市）
            all_stocks = []
            
            # 获取上市状态的股票
            for status in ['L', 'D', 'P']:  # L:上市 D:退市 P:暂停上市
                df = pro.stock_basic(
                    exchange='',
                    list_status=status,
                    fields='ts_code,symbol,name,area,industry,market,list_date,is_hs'
                )
                if df is not None and not df.empty:
                    df['list_status'] = status
                    all_stocks.append(df)
                    logger.info(f"  📊 获取状态[{status}]: {len(df)}条")
            
            if not all_stocks:
                logger.warning("⚠️ Tushare返回空数据")
                return 0
            
            # 合并所有数据
            stock_df = pd.concat(all_stocks, ignore_index=True)
            
            # 转换为MongoDB文档格式并批量更新
            count = self._bulk_upsert(stock_df, source='tushare')
            
            logger.info(f"✅ Tushare同步完成: {count}条记录")
            return count
            
        except Exception as e:
            logger.error(f"❌ Tushare同步失败: {e}")
            return -1
    
    def sync_from_akshare(self) -> int:
        """
        从AKShare同步A股上市公司数据
        
        Returns:
            int: 同步的记录数，失败返回-1
        """
        if not self.connected:
            logger.error("❌ MongoDB未连接")
            return -1
        
        if not AKSHARE_AVAILABLE:
            logger.error("❌ AKShare库未安装")
            return -1
        
        try:
            logger.info("🔄 从AKShare同步A股上市公司数据...")
            
            # 获取股票代码和名称列表
            stock_list = ak.stock_info_a_code_name()
            
            if stock_list is None or stock_list.empty:
                logger.warning("⚠️ AKShare返回空数据")
                return 0
            
            logger.info(f"  📊 获取基础列表: {len(stock_list)}条")
            
            # AKShare返回的字段较少，需要补充
            stock_list = stock_list.rename(columns={'code': 'symbol'})
            
            # 根据股票代码判断交易所和市场
            stock_list['exchange'] = stock_list['symbol'].apply(self._get_exchange)
            stock_list['market'] = stock_list['symbol'].apply(self._get_market)
            stock_list['ts_code'] = stock_list.apply(
                lambda x: f"{x['symbol']}.{x['exchange']}", axis=1
            )
            stock_list['list_status'] = 'L'  # AKShare默认返回上市股票
            
            # 转换为MongoDB文档格式并批量更新
            count = self._bulk_upsert(stock_list, source='akshare')
            
            logger.info(f"✅ AKShare同步完成: {count}条记录")
            return count
            
        except Exception as e:
            logger.error(f"❌ AKShare同步失败: {e}")
            return -1
    
    def _get_exchange(self, symbol: str) -> str:
        """根据股票代码判断交易所"""
        if symbol.startswith(('60', '68')):
            return 'SH'
        elif symbol.startswith(('00', '30', '20')):
            return 'SZ'
        elif symbol.startswith(('4', '8')):
            return 'BJ'
        return 'SZ'
    
    def _get_market(self, symbol: str) -> str:
        """根据股票代码判断市场类型"""
        if symbol.startswith('60'):
            return '主板'
        elif symbol.startswith('00'):
            return '主板'
        elif symbol.startswith('30'):
            return '创业板'
        elif symbol.startswith('68'):
            return '科创板'
        elif symbol.startswith(('4', '8')):
            return '北交所'
        elif symbol.startswith('20'):
            return 'B股'
        return '主板'
    
    def _bulk_upsert(self, df: pd.DataFrame, source: str) -> int:
        """批量更新或插入数据"""
        from pymongo import UpdateOne
        
        now = datetime.now()
        operations = []
        
        for _, row in df.iterrows():
            doc = {
                'symbol': row.get('symbol', ''),
                'ts_code': row.get('ts_code', ''),
                'name': row.get('name', ''),
                'market': row.get('market', ''),
                'exchange': row.get('exchange', ''),
                'industry': row.get('industry', ''),
                'area': row.get('area', ''),
                'list_date': row.get('list_date', ''),
                'list_status': row.get('list_status', 'L'),
                'is_hs': row.get('is_hs', ''),
                'source': source,
                'updated_at': now
            }
            
            # 清理空值
            doc = {k: v for k, v in doc.items() if v is not None and v != ''}
            doc['updated_at'] = now
            
            operations.append(
                UpdateOne(
                    {'symbol': doc['symbol']},
                    {
                        '$set': doc,
                        '$setOnInsert': {'created_at': now}
                    },
                    upsert=True
                )
            )
        
        if operations:
            result = self.collection.bulk_write(operations)
            return result.upserted_count + result.modified_count
        
        return 0
    
    # ==================== 查询方法 ====================
    
    def get_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        根据股票代码查询
        
        Args:
            symbol: 股票代码（6位数字）
            
        Returns:
            Dict: 股票信息，不存在返回None
        """
        if not self.connected:
            return None
        
        try:
            result = self.collection.find_one({'symbol': symbol}, {'_id': 0})
            return result
        except Exception as e:
            logger.error(f"❌ 查询失败: {e}")
            return None
    
    def get_by_name(self, name: str, exact: bool = False) -> List[Dict[str, Any]]:
        """
        根据股票名称查询
        
        Args:
            name: 股票名称（支持模糊查询）
            exact: 是否精确匹配
            
        Returns:
            List[Dict]: 股票信息列表
        """
        if not self.connected:
            return []
        
        try:
            if exact:
                query = {'name': name}
            else:
                query = {'name': {'$regex': name, '$options': 'i'}}
            
            results = list(self.collection.find(query, {'_id': 0}))
            return results
        except Exception as e:
            logger.error(f"❌ 查询失败: {e}")
            return []
    
    def get_by_industry(self, industry: str) -> List[Dict[str, Any]]:
        """
        根据行业查询
        
        Args:
            industry: 行业名称
            
        Returns:
            List[Dict]: 股票信息列表
        """
        if not self.connected:
            return []
        
        try:
            query = {'industry': {'$regex': industry, '$options': 'i'}}
            results = list(self.collection.find(query, {'_id': 0}))
            return results
        except Exception as e:
            logger.error(f"❌ 查询失败: {e}")
            return []
    
    def get_by_market(self, market: str) -> List[Dict[str, Any]]:
        """
        根据市场类型查询
        
        Args:
            market: 市场类型（主板/创业板/科创板/北交所）
            
        Returns:
            List[Dict]: 股票信息列表
        """
        if not self.connected:
            return []
        
        try:
            results = list(self.collection.find({'market': market}, {'_id': 0}))
            return results
        except Exception as e:
            logger.error(f"❌ 查询失败: {e}")
            return []
    
    def get_by_exchange(self, exchange: str) -> List[Dict[str, Any]]:
        """
        根据交易所查询
        
        Args:
            exchange: 交易所代码（SH/SZ/BJ）
            
        Returns:
            List[Dict]: 股票信息列表
        """
        if not self.connected:
            return []
        
        try:
            results = list(self.collection.find({'exchange': exchange.upper()}, {'_id': 0}))
            return results
        except Exception as e:
            logger.error(f"❌ 查询失败: {e}")
            return []
    
    def get_all(self, list_status: str = 'L') -> List[Dict[str, Any]]:
        """
        获取所有股票
        
        Args:
            list_status: 上市状态（L:上市, D:退市, P:暂停, None:全部）
            
        Returns:
            List[Dict]: 股票信息列表
        """
        if not self.connected:
            return []
        
        try:
            query = {}
            if list_status:
                query['list_status'] = list_status
            
            results = list(self.collection.find(query, {'_id': 0}))
            return results
        except Exception as e:
            logger.error(f"❌ 查询失败: {e}")
            return []
    
    def search(self, keyword: str) -> List[Dict[str, Any]]:
        """
        综合搜索（支持代码、名称模糊匹配）
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            List[Dict]: 股票信息列表
        """
        if not self.connected:
            return []
        
        try:
            query = {
                '$or': [
                    {'symbol': {'$regex': keyword, '$options': 'i'}},
                    {'name': {'$regex': keyword, '$options': 'i'}},
                    {'ts_code': {'$regex': keyword, '$options': 'i'}}
                ]
            }
            results = list(self.collection.find(query, {'_id': 0}).limit(50))
            return results
        except Exception as e:
            logger.error(f"❌ 搜索失败: {e}")
            return []
    
    def get_stock_name(self, symbol: str) -> str:
        """
        快速获取股票名称
        
        Args:
            symbol: 股票代码
            
        Returns:
            str: 股票名称，不存在返回空字符串
        """
        result = self.get_by_symbol(symbol)
        return result.get('name', '') if result else ''
    
    def exists(self, symbol: str) -> bool:
        """
        检查股票是否存在
        
        Args:
            symbol: 股票代码
            
        Returns:
            bool: 是否存在
        """
        if not self.connected:
            return False
        
        try:
            count = self.collection.count_documents({'symbol': symbol})
            return count > 0
        except Exception as e:
            logger.error(f"❌ 检查失败: {e}")
            return False
    
    # ==================== 统计方法 ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取字典表统计信息
        
        Returns:
            Dict: 统计信息
        """
        if not self.connected:
            return {}
        
        try:
            pipeline = [
                {
                    '$group': {
                        '_id': None,
                        'total': {'$sum': 1},
                        'exchanges': {'$addToSet': '$exchange'},
                        'markets': {'$addToSet': '$market'}
                    }
                }
            ]
            
            result = list(self.collection.aggregate(pipeline))
            
            if result:
                stats = result[0]
                # 按交易所统计
                exchange_stats = {}
                for ex in ['SH', 'SZ', 'BJ']:
                    exchange_stats[ex] = self.collection.count_documents({'exchange': ex})
                
                # 按市场统计
                market_stats = {}
                for mk in ['主板', '创业板', '科创板', '北交所']:
                    market_stats[mk] = self.collection.count_documents({'market': mk})
                
                # 按状态统计
                status_stats = {}
                for st in ['L', 'D', 'P']:
                    status_stats[st] = self.collection.count_documents({'list_status': st})
                
                return {
                    'total': stats['total'],
                    'by_exchange': exchange_stats,
                    'by_market': market_stats,
                    'by_status': status_stats,
                    'last_updated': self._get_last_updated()
                }
            
            return {'total': 0}
            
        except Exception as e:
            logger.error(f"❌ 统计失败: {e}")
            return {}
    
    def _get_last_updated(self) -> Optional[datetime]:
        """获取最后更新时间"""
        try:
            result = self.collection.find_one(
                {},
                {'updated_at': 1},
                sort=[('updated_at', DESCENDING)]
            )
            return result.get('updated_at') if result else None
        except Exception:
            return None
    
    def count(self, query: Dict = None) -> int:
        """
        统计记录数
        
        Args:
            query: 查询条件
            
        Returns:
            int: 记录数
        """
        if not self.connected:
            return 0
        
        try:
            return self.collection.count_documents(query or {})
        except Exception as e:
            logger.error(f"❌ 统计失败: {e}")
            return 0


# 单例实例
stock_dict_manager = StockDictManager()


# ==================== 直接执行入口 ====================

def main():
    """
    主函数 - 用于直接执行建表和数据同步
    
    使用方式:
        python -m tradingagents.storage.mongodb.stock_dict_manager [--source tushare|akshare] [--stats]
    
    参数:
        --source: 数据源，默认tushare（数据更全），可选akshare（免费无限制）
        --stats: 仅显示统计信息，不进行同步
        --query: 测试查询，输入股票代码
    """
    parser = argparse.ArgumentParser(
        description='A股上市公司字典表管理器 - 建表与数据同步',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m tradingagents.storage.mongodb.stock_dict_manager              # 使用Tushare同步
  python -m tradingagents.storage.mongodb.stock_dict_manager --source akshare  # 使用AKShare同步
  python -m tradingagents.storage.mongodb.stock_dict_manager --stats      # 仅查看统计
  python -m tradingagents.storage.mongodb.stock_dict_manager --query 000001  # 测试查询
        """
    )
    parser.add_argument(
        '--source', 
        choices=['tushare', 'akshare'], 
        default='tushare',
        help='数据源: tushare(默认,数据全) 或 akshare(免费)'
    )
    parser.add_argument(
        '--stats', 
        action='store_true',
        help='仅显示统计信息，不进行数据同步'
    )
    parser.add_argument(
        '--query',
        type=str,
        help='测试查询指定股票代码'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("📊 A股上市公司字典表管理器")
    print("=" * 60)
    
    # 检查MongoDB连接
    if not stock_dict_manager.connected:
        print("❌ MongoDB未连接，请检查配置")
        print("   确保MongoDB服务已启动，并正确配置环境变量")
        sys.exit(1)
    
    print(f"✅ MongoDB连接成功: {stock_dict_manager.COLLECTION_NAME}")
    
    # 测试查询模式
    if args.query:
        print(f"\n🔍 查询股票: {args.query}")
        result = stock_dict_manager.get_by_symbol(args.query)
        if result:
            print(f"   代码: {result.get('symbol')}")
            print(f"   名称: {result.get('name')}")
            print(f"   市场: {result.get('market')}")
            print(f"   交易所: {result.get('exchange')}")
            print(f"   行业: {result.get('industry', 'N/A')}")
            print(f"   地区: {result.get('area', 'N/A')}")
            print(f"   上市日期: {result.get('list_date', 'N/A')}")
            print(f"   状态: {result.get('list_status')}")
        else:
            print(f"   ⚠️ 未找到该股票，请先同步数据")
        return
    
    # 仅统计模式
    if args.stats:
        stats = stock_dict_manager.get_stats()
        if stats:
            print(f"\n📈 字典表统计信息:")
            print(f"   总记录数: {stats.get('total', 0)}")
            print(f"\n   按交易所:")
            for ex, cnt in stats.get('by_exchange', {}).items():
                print(f"      {ex}: {cnt}")
            print(f"\n   按市场:")
            for mk, cnt in stats.get('by_market', {}).items():
                print(f"      {mk}: {cnt}")
            print(f"\n   按状态:")
            status_names = {'L': '上市', 'D': '退市', 'P': '暂停'}
            for st, cnt in stats.get('by_status', {}).items():
                print(f"      {status_names.get(st, st)}: {cnt}")
            if stats.get('last_updated'):
                print(f"\n   最后更新: {stats['last_updated']}")
        else:
            print("   ⚠️ 暂无数据，请先执行同步")
        return
    
    # 数据同步模式
    print(f"\n🔄 开始从 {args.source.upper()} 同步数据...")
    print("-" * 40)
    
    if args.source == 'tushare':
        # 检查Tushare token
        token = os.getenv('TUSHARE_TOKEN', '')
        if not token:
            print("❌ 未找到TUSHARE_TOKEN环境变量")
            print("   请设置: export TUSHARE_TOKEN=your_token")
            print("   或使用AKShare: --source akshare")
            sys.exit(1)
        count = stock_dict_manager.sync_from_tushare(token)
    else:
        count = stock_dict_manager.sync_from_akshare()
    
    print("-" * 40)
    
    if count > 0:
        print(f"✅ 同步完成! 共 {count} 条记录")
        
        # 显示统计
        stats = stock_dict_manager.get_stats()
        if stats:
            print(f"\n📈 当前统计:")
            print(f"   总数: {stats.get('total', 0)}")
            print(f"   上市: {stats.get('by_status', {}).get('L', 0)}")
            print(f"   退市: {stats.get('by_status', {}).get('D', 0)}")
    elif count == 0:
        print("⚠️ 未获取到数据")
    else:
        print("❌ 同步失败，请检查日志")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("💡 提示: 使用 --stats 查看统计，--query <代码> 测试查询")
    print("=" * 60)


if __name__ == "__main__":
    main()

