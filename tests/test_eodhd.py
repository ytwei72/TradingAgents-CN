import requests

api_token = '68d5f7cdbf6a38.99947543'  # 替换为你的API密钥
ticker = '600519.SHG'  # 贵州茅台A股代码
# ticker = 'aapl.us'  # 苹果公司美股代码
# ticker = '000001.SHE'  # 平安银行A股代码
# ticker = '605507.SHG'  # 国邦医药A股代码
url = f'https://eodhd.com/api/news?s={ticker}&offset=0&limit=10&api_token={api_token}&fmt=json'

response = requests.get(url)
data = response.json()
print(data[0])
# https://eodhd.com/api/news?s=000001.SHE&api_token=68d5f7cdbf6a38.99947543&fmt=json
