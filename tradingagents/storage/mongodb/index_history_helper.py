#!/usr/bin/env python3
"""
指数历史数据管理器
用于从MongoDB集合中读取指数历史数据，如果读不到，则从在线API获取后存储到数据库

集合名称: a_index_his_trans
数据库: tradingagents (MongoDB)
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd

from tradingagents.utils.logging_manager import get_logger
logger = get_logger('storage')

try:
    from pymongo import ASCENDING, DESCENDING
    from pymongo.operations import UpdateOne
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    UpdateOne = None
    logger.warning("pymongo未安装，MongoDB功能不可用")


class IndexHistoryHelper:
    """指数历史数据管理器"""
    
    # 集合名称
    COLLECTION_NAME = "NO_USE_a_index_his_trans"
    
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
            # 复合索引：指数代码 + 日期（最常用的查询组合）
            self.collection.create_index([
                ("code", ASCENDING),
                ("date", DESCENDING)
            ])
            
            # 唯一索引：指数代码 + 日期（避免重复数据）
            self.collection.create_index([
                ("code", ASCENDING),
                ("date", ASCENDING)
            ], unique=True)
            
            # 单字段索引
            self.collection.create_index("code")
            self.collection.create_index("date")
            
            logger.info("✅ a_index_his_trans索引创建成功")
            
        except Exception as e:
            logger.error(f"❌ a_index_his_trans索引创建失败: {e}")
    
    def get_index_history(
        self,
        index_code: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        获取指数指定日期区间的历史数据
        如果数据库中不存在，则从在线API获取并存储到数据库
        
        Args:
            index_code: 指数代码（如：000001、399001）
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）
        
        Returns:
            pd.DataFrame: 指数历史数据，包含以下列：
                - date: 交易日期
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - close: 收盘价
                - preclose: 前收盘价（如果可用）
                - volume: 成交量（如果可用）
                - amount: 成交额（如果可用）
                - pctChg: 涨跌幅%（如果可用）
                如果查询失败或数据为空，返回空的DataFrame
        """
        # 1. 首先尝试从数据库读取
        df_from_db = self._get_index_history_from_db(index_code, start_date, end_date)
        
        # 2. 检查数据完整性
        if df_from_db is not None and not df_from_db.empty:
            # 检查日期范围是否完整
            if 'date' in df_from_db.columns:
                try:
                    start_dt = pd.to_datetime(start_date)
                    end_dt = pd.to_datetime(end_date)
                    df_from_db['date'] = pd.to_datetime(df_from_db['date'])
                    
                    # 从dict_trading_dates集合获取交易日列表
                    trading_dates_set = self._get_trading_dates_from_dict(start_date, end_date)
                    
                    if trading_dates_set:
                        # 使用交易日列表检查缺失日期
                        existing_dates = set(df_from_db['date'].dt.date)
                        missing_dates = [
                            date for date in trading_dates_set 
                            if date not in existing_dates
                        ]
                        
                        if not missing_dates:
                            # 数据完整，直接返回
                            df_from_db['date'] = df_from_db['date'].dt.strftime('%Y-%m-%d')
                            logger.info(f"✅ 从数据库获取指数{index_code}历史数据成功: {len(df_from_db)}条（{start_date}至{end_date}）")
                            return df_from_db
                        else:
                            logger.info(f"⚠️ 指数{index_code}数据库中存在部分数据，缺失{len(missing_dates)}个交易日，将从API补充")
                    else:
                        # 如果无法从dict_trading_dates获取，使用简单的周末排除方法作为后备
                        date_range = pd.date_range(start=start_dt, end=end_dt, freq='D')
                        existing_dates = set(df_from_db['date'].dt.date)
                        missing_dates = [
                            d.date() for d in date_range 
                            if d.date() not in existing_dates and d.weekday() < 5  # 排除周末
                        ]
                        
                        if not missing_dates:
                            df_from_db['date'] = df_from_db['date'].dt.strftime('%Y-%m-%d')
                            logger.info(f"✅ 从数据库获取指数{index_code}历史数据成功: {len(df_from_db)}条（{start_date}至{end_date}）")
                            return df_from_db
                        else:
                            logger.info(f"⚠️ 指数{index_code}数据库中存在部分数据，缺失{len(missing_dates)}个可能的交易日，将从API补充")
                except Exception as e:
                    logger.warning(f"检查数据完整性时出错: {e}，将从API重新获取")
        
        # 3. 从在线API获取数据
        logger.info(f"从在线API获取指数{index_code}数据（{start_date}至{end_date}）")
        df_from_api = self._get_index_data_from_api(index_code, start_date, end_date)
        
        if df_from_api is None or df_from_api.empty:
            # 如果API也获取失败，返回数据库中的数据（如果有）
            if df_from_db is not None and not df_from_db.empty:
                logger.warning(f"⚠️ API获取失败，返回数据库中已有数据: {len(df_from_db)}条")
                return df_from_db
            return pd.DataFrame()
        
        # 4. 将API获取的数据存储到数据库
        try:
            self._save_index_history_to_db(index_code, df_from_api)
            logger.info(f"✅ 已将从API获取的指数{index_code}数据保存到数据库: {len(df_from_api)}条")
        except Exception as e:
            logger.warning(f"⚠️ 保存指数数据到数据库失败: {e}，但不影响返回数据")
        
        return df_from_api
    
    def _get_index_history_from_db(
        self,
        index_code: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """
        从数据库读取指数历史数据
        
        Args:
            index_code: 指数代码
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            pd.DataFrame: 指数历史数据，如果查询失败返回None
        """
        if not self.connected:
            return None
        
        try:
            # 将字符串日期转换为datetime对象
            try:
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
            except Exception as e:
                logger.error(f"日期格式转换失败: {e}")
                return None
            
            # 构建查询条件
            query = {
                'code': index_code,
                'date': {
                    '$gte': start_dt.to_pydatetime(),
                    '$lte': end_dt.to_pydatetime()
                }
            }
            
            # 查询数据
            cursor = self.collection.find(query).sort('date', ASCENDING)
            records = list(cursor)
            
            if not records:
                return None
            
            # 转换为DataFrame
            df = pd.DataFrame(records)
            
            # 移除_id字段
            if '_id' in df.columns:
                df = df.drop(columns=['_id'])
            
            # 确保date列存在且为字符串格式
            if 'date' not in df.columns:
                logger.warning(f"指数数据缺少date列: {list(df.columns)}")
                return None
            
            # 确保date列是字符串格式
            if pd.api.types.is_datetime64_any_dtype(df['date']):
                df['date'] = df['date'].dt.strftime('%Y-%m-%d')
            elif len(df) > 0 and not isinstance(df['date'].iloc[0], str):
                df['date'] = df['date'].astype(str)
            
            # 确保close列为数值类型
            if 'close' in df.columns:
                df['close'] = pd.to_numeric(df['close'], errors='coerce')
            
            # 按日期排序
            df = df.sort_values('date').reset_index(drop=True)
            
            return df
            
        except Exception as e:
            logger.error(f"❌ 从数据库获取指数历史数据失败: {e}", exc_info=True)
            return None
    
    def _get_trading_dates_from_dict(self, start_date: str, end_date: str) -> Optional[set]:
        """
        从dict_trading_dates集合获取指定日期范围内的交易日集合
        
        Args:
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）
        
        Returns:
            set: 交易日集合（date对象），如果获取失败返回None
        """
        if not self.connected:
            return None
        
        try:
            from tradingagents.storage.manager import get_mongo_collection
            
            # 获取dict_trading_dates集合
            trading_dates_collection = get_mongo_collection("dict_trading_dates")
            if trading_dates_collection is None:
                logger.debug("dict_trading_dates集合不可用")
                return None
            
            # 将字符串日期转换为datetime对象
            try:
                start_dt = pd.to_datetime(start_date).to_pydatetime()
                end_dt = pd.to_datetime(end_date).to_pydatetime()
            except Exception as e:
                logger.warning(f"日期格式转换失败: {e}")
                return None
            
            # 查询交易日（尝试不同的字段名）
            query_candidates = [
                {'date': {'$gte': start_dt, '$lte': end_dt}},
                {'trade_date': {'$gte': start_dt, '$lte': end_dt}},
                {'date': {'$gte': start_date, '$lte': end_date}},  # 字符串格式
                {'trade_date': {'$gte': start_date, '$lte': end_date}},  # 字符串格式
            ]
            
            trading_dates = set()
            for query in query_candidates:
                try:
                    cursor = trading_dates_collection.find(query)
                    records = list(cursor)
                    
                    if records:
                        # 确定日期字段名
                        date_field = None
                        if 'date' in query:
                            date_field = 'date'
                        elif 'trade_date' in query:
                            date_field = 'trade_date'
                        
                        if date_field:
                            for record in records:
                                if date_field in record:
                                    date_val = record[date_field]
                                    # 转换为date对象
                                    if isinstance(date_val, datetime):
                                        trading_dates.add(date_val.date())
                                    elif isinstance(date_val, str):
                                        try:
                                            dt = pd.to_datetime(date_val).to_pydatetime()
                                            trading_dates.add(dt.date())
                                        except:
                                            pass
                        
                        if trading_dates:
                            logger.debug(f"从dict_trading_dates获取到{len(trading_dates)}个交易日（{start_date}至{end_date}）")
                            return trading_dates
                except Exception as e:
                    logger.debug(f"查询dict_trading_dates失败（查询: {query}）: {e}")
                    continue
            
            # 如果没有找到数据，尝试查找集合中所有记录的字段结构
            try:
                sample = trading_dates_collection.find_one()
                if sample:
                    logger.debug(f"dict_trading_dates集合示例记录字段: {list(sample.keys())}")
            except:
                pass
            
            logger.debug(f"无法从dict_trading_dates获取交易日列表")
            return None
            
        except Exception as e:
            logger.debug(f"从dict_trading_dates获取交易日列表失败: {e}")
            return None
    
    def _get_index_data_from_api(
        self,
        index_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """
        从在线API获取指数历史数据（采用BacktestService中的方式）
        优先使用 BaoStock，失败时回退到 Tushare

        Args:
            index_code: 指数代码（如：000001、399001）
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）

        Returns:
            pd.DataFrame: 指数历史数据，包含date和close列
        """
        # 1. 优先尝试 BaoStock
        try:
            try:
                import baostock as bs  # type: ignore
            except ImportError:
                bs = None

            if bs is not None:
                # BaoStock 指数代码映射，例如：上证指数 sh.000001，深证成指 sz.399001
                if index_code == "000001":
                    bs_code = "sh.000001"
                elif index_code == "399001":
                    bs_code = "sz.399001"
                else:
                    # 简单推断：39* 为深市，00* 为沪市
                    if index_code.startswith("39"):
                        bs_code = f"sz.{index_code}"
                    elif index_code.startswith("00"):
                        bs_code = f"sh.{index_code}"
                    else:
                        bs_code = index_code

                lg = bs.login()
                if lg.error_code != "0":
                    logger.warning(f"⚠️ BaoStock 登录失败: {lg.error_msg}")
                else:
                    try:
                        # 获取更多字段：日期、开盘、最高、最低、收盘、前收盘、成交量、成交额、涨跌幅
                        rs = bs.query_history_k_data_plus(
                            bs_code,
                            "date,open,high,low,close,preclose,volume,amount,pctChg",
                            start_date=start_date,
                            end_date=end_date,
                            frequency="d",
                            adjustflag="3",  # 不复权
                        )
                        if rs.error_code != "0":
                            logger.warning(f"⚠️ BaoStock 指数查询失败: {rs.error_msg}")
                        else:
                            data_list: list[list[str]] = []
                            while rs.error_code == "0" and rs.next():
                                data_list.append(rs.get_row_data())

                            if data_list:
                                df = pd.DataFrame(data_list, columns=rs.fields)
                                # 确保列名与类型
                                if "date" in df.columns and "close" in df.columns:
                                    # 日期列转换为字符串格式
                                    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
                                    
                                    # 数值列转换为数值类型
                                    numeric_columns = ["open", "high", "low", "close", "preclose", "volume", "amount", "pctChg"]
                                    for col in numeric_columns:
                                        if col in df.columns:
                                            df[col] = pd.to_numeric(df[col], errors="coerce")
                                    
                                    df = df.sort_values("date").reset_index(drop=True)
                                    logger.info(
                                        f"✅ BaoStock 获取指数{index_code}数据成功: {len(df)}条（{start_date}至{end_date}）"
                                    )
                                    bs.logout()
                                    return df
                                else:
                                    logger.warning(f"⚠️ BaoStock 指数数据缺少必要列: {list(df.columns)}")
                    except Exception as bs_e:
                        logger.warning(f"⚠️ BaoStock 获取指数{index_code}数据异常: {bs_e}")
                    finally:
                        try:
                            bs.logout()
                        except Exception:
                            pass
        except Exception as e:
            logger.debug(f"BaoStock 指数数据获取阶段异常: {e}", exc_info=True)

        # 2. 回退到 Tushare
        try:
            from tradingagents.dataflows.tushare_adapter import get_tushare_adapter

            adapter = get_tushare_adapter()
            if adapter and adapter.provider and adapter.provider.connected:
                # 对于指数，需要转换为Tushare标准格式
                if index_code == "000001":
                    # 上证指数
                    index_symbols = ["000001.SH", "000001"]
                elif index_code == "399001":
                    # 深证成指
                    index_symbols = ["399001.SZ", "399001"]
                else:
                    # 尝试自动判断交易所
                    if index_code.startswith("39"):
                        index_symbols = [f"{index_code}.SZ", index_code]
                    elif index_code.startswith("00"):
                        index_symbols = [f"{index_code}.SH", index_code]
                    else:
                        index_symbols = [index_code]

                for symbol in index_symbols:
                    try:
                        df = adapter.provider.get_index_daily(symbol, start_date, end_date)
                        if df is not None and not df.empty:
                            # 标准化列名
                            if "trade_date" in df.columns:
                                df["date"] = df["trade_date"]
                            elif "date" not in df.columns:
                                logger.warning(f"指数数据缺少date列: {list(df.columns)}")
                                continue

                            # 确保date列是字符串格式
                            if "date" in df.columns:
                                df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

                            # 标准化close列名（必要字段）
                            if "close" not in df.columns:
                                logger.warning(f"指数数据缺少close列: {list(df.columns)}")
                                continue

                            # 标准化其他可能存在的列名
                            column_mapping = {
                                "open": ["open"],
                                "high": ["high"],
                                "low": ["low"],
                                "preclose": ["pre_close", "preclose"],
                                "volume": ["vol", "volume"],
                                "amount": ["amount"],
                                "pctChg": ["pct_chg", "pctChg", "change_pct"],
                            }
                            
                            # 映射列名
                            for standard_col, possible_cols in column_mapping.items():
                                if standard_col not in df.columns:
                                    for possible_col in possible_cols:
                                        if possible_col in df.columns:
                                            df[standard_col] = df[possible_col]
                                            break

                            # 确保数值列为数值类型
                            numeric_columns = ["open", "high", "low", "close", "preclose", "volume", "amount", "pctChg"]
                            for col in numeric_columns:
                                if col in df.columns:
                                    df[col] = pd.to_numeric(df[col], errors="coerce")

                            # 按日期排序
                            df = df.sort_values("date").reset_index(drop=True)

                            logger.info(f"✅ Tushare 获取指数{index_code}数据成功: {len(df)}条（{start_date}至{end_date}）")
                            return df
                    except Exception as e:
                        logger.debug(f"尝试获取指数{symbol}数据失败: {e}")
                        continue

                logger.warning(f"⚠️ 无法获取指数{index_code}数据（尝试了所有符号格式）")
                return pd.DataFrame()
            else:
                logger.warning("⚠️ Tushare适配器不可用，无法获取指数数据")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"❌ 获取指数{index_code}数据失败: {e}", exc_info=True)
            return pd.DataFrame()
    
    def _save_index_history_to_db(
        self,
        index_code: str,
        df: pd.DataFrame
    ) -> bool:
        """
        将指数历史数据保存到数据库
        
        Args:
            index_code: 指数代码
            df: 指数历史数据DataFrame，必须包含date和close列
        
        Returns:
            bool: 是否保存成功
        """
        if not self.connected:
            logger.error("❌ MongoDB未连接，无法保存数据")
            return False
        
        if df.empty or 'date' not in df.columns or 'close' not in df.columns:
            logger.error("❌ 数据格式错误：缺少date或close列")
            return False
        
        # 定义需要保存的字段列表（date和code用于查询条件，不在$set中）
        save_fields = ['open', 'high', 'low', 'close', 'preclose', 'volume', 'amount', 'pctChg']
        
        try:
            # 准备批量插入的数据
            records = []
            for _, row in df.iterrows():
                date_str = row['date']
                
                # 将日期字符串转换为datetime对象
                try:
                    if isinstance(date_str, str):
                        date_dt = pd.to_datetime(date_str).to_pydatetime()
                    else:
                        date_dt = pd.to_datetime(date_str).to_pydatetime()
                except Exception as e:
                    logger.warning(f"日期转换失败: {date_str}, {e}")
                    continue
                
                # 构建记录，包含所有可用字段
                record = {
                    'code': index_code,
                    'date': date_dt,
                }
                
                # 添加需要保存的字段
                for field in save_fields:
                    if field in df.columns:
                        value = row[field]
                        if pd.notna(value):
                            # 根据字段类型转换
                            if field in ['volume', 'amount']:
                                # 成交量和成交额可能是整数或浮点数
                                try:
                                    record[field] = float(value)
                                except (ValueError, TypeError):
                                    record[field] = None
                            elif field in ['open', 'high', 'low', 'close', 'preclose', 'pctChg']:
                                # 价格和涨跌幅为浮点数
                                try:
                                    record[field] = float(value)
                                except (ValueError, TypeError):
                                    record[field] = None
                            else:
                                record[field] = value
                
                # 添加其他可能存在的列（不在标准字段列表中的）
                for col in df.columns:
                    if col not in ['date', 'code'] and col not in save_fields:
                        value = row[col]
                        if pd.notna(value):
                            # 尝试转换为数值类型，如果失败则保留原值
                            try:
                                num_value = pd.to_numeric(value, errors='coerce')
                                if pd.notna(num_value):
                                    record[col] = float(num_value) if isinstance(num_value, (int, float)) else value
                                else:
                                    record[col] = value
                            except (ValueError, TypeError):
                                record[col] = value
                
                records.append(record)
            
            if not records:
                logger.warning("⚠️ 没有有效数据需要保存")
                return False
            
            # 批量插入（使用upsert，避免重复）
            bulk_ops = []
            for record in records:
                # 分离查询条件和更新数据（code和date用于查询，不放入$set）
                filter_dict = {
                    'code': record['code'],
                    'date': record['date']
                }
                # 构建更新数据（排除code和date）
                update_dict = {k: v for k, v in record.items() if k not in ['code', 'date']}
                
                bulk_ops.append(
                    UpdateOne(
                        filter_dict,
                        {'$set': update_dict},
                        upsert=True
                    )
                )
            
            if bulk_ops:
                result = self.collection.bulk_write(bulk_ops, ordered=False)
                logger.info(
                    f"✅ 保存指数{index_code}数据成功: "
                    f"插入{result.upserted_count}条，更新{result.modified_count}条"
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ 保存指数数据到数据库失败: {e}", exc_info=True)
            return False
    
    def get_latest_date(self, index_code: str) -> Optional[str]:
        """
        获取某个指数的最新交易日期
        
        Args:
            index_code: 指数代码
        
        Returns:
            str: 最新交易日期（YYYY-MM-DD格式），如果不存在返回None
        """
        if not self.connected:
            return None
        
        try:
            result = self.collection.find_one(
                {'code': index_code},
                {'date': 1},
                sort=[('date', DESCENDING)]
            )
            
            if result and 'date' in result:
                date = result['date']
                # 确保返回字符串格式
                if isinstance(date, datetime):
                    return date.strftime('%Y-%m-%d')
                return str(date)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 获取最新交易日期失败: {e}")
            return None
    
    def get_earliest_date(self, index_code: str) -> Optional[str]:
        """
        获取某个指数的最早交易日期
        
        Args:
            index_code: 指数代码
        
        Returns:
            str: 最早交易日期（YYYY-MM-DD格式），如果不存在返回None
        """
        if not self.connected:
            return None
        
        try:
            result = self.collection.find_one(
                {'code': index_code},
                {'date': 1},
                sort=[('date', ASCENDING)]
            )
            
            if result and 'date' in result:
                date = result['date']
                # MongoDB的ISODate是datetime类型，转换为字符串格式
                if isinstance(date, datetime):
                    return date.strftime('%Y-%m-%d')
                elif hasattr(date, 'strftime'):  # 兼容pandas Timestamp等类型
                    return date.strftime('%Y-%m-%d')
                # 如果已经是字符串，直接返回
                return str(date)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 获取最早交易日期失败: {e}")
            return None
    
    def count_records(
        self, 
        index_code: str, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> int:
        """
        统计指定指数在指定日期范围内的记录数
        
        Args:
            index_code: 指数代码
            start_date: 开始日期（可选，YYYY-MM-DD格式）
            end_date: 结束日期（可选，YYYY-MM-DD格式）
        
        Returns:
            int: 记录数
        """
        if not self.connected:
            return 0
        
        try:
            query = {'code': index_code}
            
            if start_date or end_date:
                date_query = {}
                # 将字符串日期转换为datetime对象
                if start_date:
                    try:
                        start_dt = pd.to_datetime(start_date)
                        date_query['$gte'] = start_dt.to_pydatetime()
                    except Exception as e:
                        logger.error(f"开始日期格式转换失败: {e}")
                        return 0
                if end_date:
                    try:
                        end_dt = pd.to_datetime(end_date)
                        date_query['$lte'] = end_dt.to_pydatetime()
                    except Exception as e:
                        logger.error(f"结束日期格式转换失败: {e}")
                        return 0
                query['date'] = date_query
            
            count = self.collection.count_documents(query)
            return count
            
        except Exception as e:
            logger.error(f"❌ 统计记录数失败: {e}")
            return 0
    
    def get_index_list(self) -> List[str]:
        """
        获取集合中所有指数代码列表
        
        Returns:
            List[str]: 指数代码列表
        """
        if not self.connected:
            return []
        
        try:
            codes = self.collection.distinct('code')
            return sorted(codes)
            
        except Exception as e:
            logger.error(f"❌ 获取指数列表失败: {e}")
            return []


# 单例实例
index_history_helper = IndexHistoryHelper()

