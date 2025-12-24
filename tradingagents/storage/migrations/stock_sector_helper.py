import akshare as ak
import pandas as pd
from utils.mongo_client import MongoDBCli
from pymongo import UpdateOne

class StockSectorHelper:
    def __init__(self):
        pass

    def fetch_industry_sector_list(self) -> list:
        """
        获取行业板块的列表。
        """
        try:
            industry_boards = ak.stock_board_industry_name_em()
            if not industry_boards.empty:
                return [{'code': row['板块代码'], 'name': row['板块名称']} for _, row in industry_boards.iterrows()]
            return []
        except Exception as e:
            print(f"获取行业板块列表失败: {e}")
            return []

    def fetch_stocks_in_industry_sector(self, sector_name: str) -> pd.DataFrame:
        """
        获取指定行业板块的上市公司的股票代码及公司名。
        """
        try:
            stocks_df = ak.stock_board_industry_cons_em(symbol=sector_name)
            if not stocks_df.empty:
                return stocks_df[['代码', '名称']].rename(columns={'代码': 'code', '名称': 'name'})
            print(f"行业板块 '{sector_name}' 下无股票数据。")
            return pd.DataFrame(columns=['code', 'name'])
        except Exception as e:
            print(f"获取行业板块 '{sector_name}' 下股票列表失败: {e}")
            return pd.DataFrame(columns=['code', 'name'])

    def fetch_concept_sector_list(self) -> list:
        """
        获取概念板块的列表。
        """
        try:
            concept_boards = ak.stock_board_concept_name_em()
            if not concept_boards.empty:
                return [{'code': row['板块代码'], 'name': row['板块名称']} for _, row in concept_boards.iterrows()]
            return []
        except Exception as e:
            print(f"获取概念板块列表失败: {e}")
            return []

    def fetch_stocks_in_concept_sector(self, sector_name: str) -> pd.DataFrame:
        """
        获取指定概念板块的上市公司的股票代码及公司名。
        """
        try:
            stocks_df = ak.stock_board_concept_cons_em(symbol=sector_name)
            if not stocks_df.empty:
                return stocks_df[['代码', '名称']].rename(columns={'代码': 'code', '名称': 'name'})
            print(f"概念板块 '{sector_name}' 下无股票数据。")
            return pd.DataFrame(columns=['code', 'name'])
        except Exception as e:
            print(f"获取概念板块 '{sector_name}' 下股票列表失败: {e}")
            return pd.DataFrame(columns=['code', 'name'])

    def _map_collection_name(self, sector_category: str) -> str:
        mapping = {'行业': 'industry_sectors', '概念': 'concept_sectors'}
        english_category = mapping[sector_category]
        collection_name = f"dict_{english_category}"

        return collection_name

    def save_sectors(self, sector_category: str, sector_list: list) -> dict:
        """
        保存板块列表到MongoDB数据库。
        :param sector_category: 板块类别 ('行业' 或 '概念')
        :param sector_list: 板块列表，每个元素为 {'code': str, 'name': str}
        :return: bulk_write 结果
        """
        if sector_category not in ['行业', '概念']:
            raise ValueError("sector_category 必须是 '行业' 或 '概念'")

        cli = MongoDBCli()
        collection_name = self._map_collection_name(sector_category)
        collection = cli.db[collection_name]

        operations = [
            UpdateOne(
                # {'code': sector['code']},
                {'name': sector['name']},
                {'$set': {'code': sector['code'], 'name': sector['name'], 'category': sector_category}},
                upsert=True
            )
            for sector in sector_list
        ]

        try:
            result = collection.bulk_write(operations)
            print(f"成功保存 {len(sector_list)} 个 {sector_category} 板块到集合 '{collection_name}'")
            return result.bulk_api_result
        except Exception as e:
            print(f"保存 {sector_category} 板块失败: {e}")
            return {}
        finally:
            cli.close()

    def save_stocks_in_sector(self, sector_category: str, sector_name: str, stock_list: list) -> dict:
        """
        保存指定板块的股票列表到MongoDB数据库。
        :param sector_category: 板块类别 ('行业' 或 '概念')
        :param sector_name: 板块名称
        :param stock_list: 股票列表，格式为 [{'code': str, 'name': str}, ...]
        :return: update_one 结果
        """
        if sector_category not in ['行业', '概念']:
            raise ValueError("sector_category 必须是 '行业' 或 '概念'")

        cli = MongoDBCli()
        collection_name = self._map_collection_name(sector_category)
        collection = cli.db[collection_name]

        try:
            result = collection.update_one(
                {'name': sector_name},
                {'$set': {'name': sector_name, 'category': sector_category, 'stocks': stock_list}},
                upsert=True
            )
            if result.upserted_id:
                print(f"成功插入板块 '{sector_name}' 的股票列表 ({len(stock_list)} 只股票) 到集合 '{collection_name}'")
            elif result.modified_count > 0:
                print(f"成功更新板块 '{sector_name}' 的股票列表 ({len(stock_list)} 只股票) 到集合 '{collection_name}'")
            else:
                print(f"板块 '{sector_name}' 的股票列表未发生变化")
            return result.raw_result
        except Exception as e:
            print(f"保存板块 '{sector_name}' 的股票列表失败: {e}")
            return {}
        finally:
            cli.close()

    def get_sectors(self, sector_category: str) -> list:
        """
        从数据库中读取指定类别的板块列表。
        :param sector_category: 板块类别 ('行业' 或 '概念')
        :return: 板块列表，每个元素为 {'code': str, 'name': str}
        """
        if sector_category not in ['行业', '概念']:
            raise ValueError("sector_category 必须是 '行业' 或 '概念'")

        cli = MongoDBCli()
        collection_name = self._map_collection_name(sector_category)
        collection = cli.db[collection_name]

        try:
            sectors = [{'code': doc['code'], 'name': doc['name']} for doc in collection.find({}, {'code': 1, 'name': 1})]
            return sorted(sectors, key=lambda x: x['name'])
        except Exception as e:
            print(f"从数据库读取 {sector_category} 板块列表失败: {e}")
            return []
        finally:
            cli.close()

    def get_stocks_in_sectors(self, sector_names: list[str], sector_category: str) -> dict:
        """
        从数据库中读取指定板块的股票列表，支持多个板块。
        :param sector_names: 板块名称列表
        :param sector_category: 板块类别 ('行业' 或 '概念')
        :return: dict, key为板块名称, value为股票列表 [{'code': str, 'name': str}, ...]
        """
        if sector_category not in ['行业', '概念']:
            raise ValueError("sector_category 必须是 '行业' 或 '概念'")

        cli = MongoDBCli()
        collection_name = self._map_collection_name(sector_category)
        collection = cli.db[collection_name]

        result = {}
        try:
            for sector_name in sector_names:
                doc = collection.find_one({'name': sector_name})
                if doc and 'stocks' in doc:
                    result[sector_name] = doc['stocks']
                else:
                    result[sector_name] = []
            return result
        except Exception as e:
            print(f"从数据库读取板块股票列表失败: {e}")
            return {sector: [] for sector in sector_names}
        finally:
            cli.close()


def test_fetch_sectors():
    """测试新增的4个板块函数"""
    helper = StockSectorHelper()

    # print("\n--- 获取行业板块列表 ---")
    # industry_sectors = helper.fetch_industry_sector_list()
    # if industry_sectors:
    #     print(f"获取到 {len(industry_sectors)} 个行业板块。")
    #     print("部分行业板块示例:", industry_sectors[:10])
    # else:
    #     print("未获取到任何行业板块。")
    #
    # print("\n--- 获取概念板块列表 ---")
    # concept_sectors = helper.fetch_concept_sector_list()
    # if concept_sectors:
    #     print(f"获取到 {len(concept_sectors)} 个概念板块。")
    #     print("部分概念板块示例:", concept_sectors[:10])
    # else:
    #     print("未获取到任何概念板块。")

    # print("\n--- 获取指定行业板块的股票列表 (例如: '证券') ---")
    # securities_stocks = helper.fetch_stocks_in_industry_sector("证券")
    # if not securities_stocks.empty:
    #     print(f"行业板块 '证券' 下有 {len(securities_stocks)} 只股票。")
    #     print(securities_stocks.head())
    # else:
    #     print("未获取到 '证券' 行业板块下的股票。")

    sector_name = '数据安全'
    print(f"\n--- 获取指定概念板块的股票列表 (例如: '{sector_name}') ---")
    ai_stocks = helper.fetch_stocks_in_concept_sector(sector_name)
    if not ai_stocks.empty:
        print(f"概念板块 '{sector_name}' 下有 {len(ai_stocks)} 只股票。")
        print(ai_stocks.head())
    else:
        print(f"未获取到 '{sector_name}' 概念板块下的股票。")

    # print("\n--- 获取一个不存在的行业板块的股票列表 ---")
    # non_existent_industry = helper.fetch_stocks_in_industry_sector("不存在的行业板块")
    # if non_existent_industry.empty:
    #     print("成功处理不存在的行业板块，返回空列表。")
    # else:
    #     print("错误：获取不存在的行业板块返回了数据。")
    #
    # print("\n--- 获取一个不存在的概念板块的股票列表 ---")
    # non_existent_concept = helper.fetch_stocks_in_concept_sector("不存在的概念板块")
    # if non_existent_concept.empty:
    #     print("成功处理不存在的概念板块，返回空列表。")
    # else:
    #     print("错误：获取不存在的概念板块返回了数据。")


def test_db_query_functions():
    """测试数据库相关的板块函数"""
    helper = StockSectorHelper()

    print("\n--- 从数据库获取行业板块列表 ---")
    industry_sectors = helper.get_sectors('行业')
    if industry_sectors:
        print(f"从数据库获取到 {len(industry_sectors)} 个行业板块。")
        print("部分行业板块示例:", [{'code': s['code'], 'name': s['name']} for s in industry_sectors[:10]])
    else:
        print("数据库中未获取到任何行业板块。")

    print("\n--- 从数据库获取概念板块列表 ---")
    concept_sectors = helper.get_sectors('概念')
    if concept_sectors:
        print(f"从数据库获取到 {len(concept_sectors)} 个概念板块。")
        print("部分概念板块示例:", [{'code': s['code'], 'name': s['name']} for s in concept_sectors[:10]])
    else:
        print("数据库中未获取到任何概念板块。")

    print("\n--- 从数据库获取多个行业板块的股票列表 (例如: ['证券', '银行']) ---")
    industry_stocks = helper.get_stocks_in_sectors(['证券', '银行'], '行业')
    for sector, stocks in industry_stocks.items():
        if stocks:
            print(f"行业板块 '{sector}' 下有 {len(stocks)} 只股票。")
            print(f"示例股票: {stocks[:3]}")  # 显示前3只
        else:
            print(f"行业板块 '{sector}' 下无股票数据。")

    print("\n--- 从数据库获取多个概念板块的股票列表 (例如: ['人工智能', '数据安全']) ---")
    concept_stocks = helper.get_stocks_in_sectors(['人工智能', '数据安全'], '概念')
    for sector, stocks in concept_stocks.items():
        if stocks:
            print(f"概念板块 '{sector}' 下有 {len(stocks)} 只股票。")
            print(f"示例股票: {stocks[:3]}")  # 显示前3只
        else:
            print(f"概念板块 '{sector}' 下无股票数据。")


def test_update_sectors_to_db():
    """测试获取板块列表并更新到数据库"""
    helper = StockSectorHelper()

    print("\n--- 更新行业板块到数据库 ---")
    industry_sectors = helper.fetch_industry_sector_list()
    if industry_sectors:
        result = helper.save_sectors('行业', industry_sectors)
        print(f"行业板块更新结果: {result}")

        # 保存示例行业板块的股票
        example_industry_sectors = ['证券', '银行']
        for sector_name in example_industry_sectors:
            stocks_df = helper.fetch_stocks_in_industry_sector(sector_name)
            if not stocks_df.empty:
                stock_list = [{'code': row['code'], 'name': row['name']} for _, row in stocks_df.iterrows()]
                stock_result = helper.save_stocks_in_sector('行业', sector_name, stock_list)
                print(f"行业板块 '{sector_name}' 股票更新结果: {stock_result}")
            else:
                print(f"未获取到行业板块 '{sector_name}' 的股票")
    else:
        print("未获取到行业板块列表")

    print("\n--- 更新概念板块到数据库 ---")
    concept_sectors = helper.fetch_concept_sector_list()
    if concept_sectors:
        result = helper.save_sectors('概念', concept_sectors)
        print(f"概念板块更新结果: {result}")

        # 保存示例概念板块的股票
        example_concept_sectors = ['人工智能', '数据安全']
        for sector_name in example_concept_sectors:
            stocks_df = helper.fetch_stocks_in_concept_sector(sector_name)
            if not stocks_df.empty:
                stock_list = [{'code': row['code'], 'name': row['name']} for _, row in stocks_df.iterrows()]
                stock_result = helper.save_stocks_in_sector('概念', sector_name, stock_list)
                print(f"概念板块 '{sector_name}' 股票更新结果: {stock_result}")
            else:
                print(f"未获取到概念板块 '{sector_name}' 的股票")
    else:
        print("未获取到概念板块列表")


if __name__ == '__main__':
    # test_fetch_sectors()
    test_db_query_functions()
    # test_update_sectors_to_db()
