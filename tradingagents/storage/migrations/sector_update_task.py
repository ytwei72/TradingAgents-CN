from sys import path
import os

# Add the project root to the Python path
path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from .stock_sector_helper import StockSectorHelper
from tasks.tasks_common import TaskCommon

class SectorUpdateTask:
    def __init__(self):
        self.helper = StockSectorHelper()

    def run(self):
        print("开始更新行业板块信息...")

        # 获取并保存行业板块列表
        industry_sectors = self.helper.fetch_industry_sector_list()
        # industry_sectors = None
        if industry_sectors:
            self.helper.save_sectors('行业', industry_sectors)
            print(f"保存了 {len(industry_sectors)} 个行业板块。")

            # 为每个行业板块获取并保存股票列表
            for sector in industry_sectors:
                TaskCommon.delay_for_period(2, 5)  # 避免请求过于频繁
                stocks_df = self.helper.fetch_stocks_in_industry_sector(sector)
                if not stocks_df.empty:
                    stock_list = stocks_df.to_dict('records')
                    self.helper.save_stocks_in_sector('行业', sector, stock_list)
                    print(f"保存了行业板块 '{sector}' 的 {len(stock_list)} 只股票。")
                else:
                    print(f"行业板块 '{sector}' 无股票数据。")
        else:
            print("未获取到行业板块列表。")

        print("行业板块更新完成。")

        print("开始更新概念板块信息...")

        # 获取并保存概念板块列表
        concept_sectors = self.helper.fetch_concept_sector_list()
        if concept_sectors:
            self.helper.save_sectors('概念', concept_sectors)
            print(f"保存了 {len(concept_sectors)} 个概念板块。")

            # 为每个概念板块获取并保存股票列表
            to_update = False # 从特定板块开始更新，解决封IP的问题
            for sector in concept_sectors:
                if sector in ['跨境电商']:
                    to_update = True
                if not to_update:
                    continue

                TaskCommon.delay_for_period(2, 5)  # 避免请求过于频繁
                stocks_df = self.helper.fetch_stocks_in_concept_sector(sector)
                if not stocks_df.empty:
                    stock_list = stocks_df.to_dict('records')
                    self.helper.save_stocks_in_sector('概念', sector, stock_list)
                    print(f"保存了概念板块 '{sector}' 的 {len(stock_list)} 只股票。")
                else:
                    print(f"概念板块 '{sector}' 无股票数据。")
        else:
            print("未获取到概念板块列表。")

        print("概念板块更新完成。")
        print("板块资料更新任务完成。")

if __name__ == "__main__":
    task = SectorUpdateTask()
    task.run()