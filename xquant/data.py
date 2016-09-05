# -*- coding: utf-8 -*-

"""
DataHandler抽象基类
数据处理不区分历史数据还是实时数据

@author: X0Leon
@version: 0.1
"""

import datetime
import os, os.path
import pandas as pandas

from abc import ABCMeta, abstractmethod

from event import MarketEvent

class DataHandler(object):
	"""
	DataHandler抽象基本，不允许直接实例化，只用于继承
	继承的DataHandler对象用于对每个symbol生成bars序列（OLHCV）
	这里不区分历史数据和实时交易数据
	"""
	__metaclass__ = ABCMeta

	@abstractmethod
	def get_latest_bars(self, symbol, N=1):
		"""
		从latest_symbol列表中返回最近的几根bar，
		如果可用值小于N，则返回更少
		"""
		raise NotImplementedError("未实现get_latest_bars()，此方法是必须的！")

	@abstractmethod
	def update_bars(self):
		"""
		将股票列表中bar(条状图)更新到最近的那一根
		"""
		raise NotImplementedError("未实现update_bars()，此方法是必须的！")


##### 实现更具体地数据处理类，例如CSVDataHandler, HDF5DataHandler, BrokersDataHandler等
##### 这里先实现第一个，稍后实现第二个
class CSVDataHandler(DataHandler):
	"""
	CSVDataHandler类用于从硬盘中读取csv格式的历史数据，并实现最新的bar模拟实时交易的情况
	"""
	def __init__(self, events, csv_dir, symbol_list):
		"""
		初始化历史数据的处理，假设文件以股票代码+csv格式存储，如600008.csv
		参数：
		events: 时间队列（Event Queue）
		cdv_dir：CSV文件的绝对路径，如"d:/datasources/"或者使用“d:\\..."
		symbol_list: 股票代码列表，如['600008', '600018']
		"""
		self.events = events
		self.csv_dir = csv_dir
		self.symbol_list = symbol_list

		self.symbol_data = {}
		self.latest_symbol_data = {}
		self.continue_backtest = True

		self._open_convert_csv_files()

		def _open_convert_csv_files(self):
			"""
			从数据文件夹中打开CSV文件，转换成pandas的DataFrames格式
			用_开头说明这是一个仅供内部使用的方法，一般情况下不要在外部调用
			TODO:
			    明确无误地选择一个格式，tushare的df转换成csv的格式？
			    'datetime','open','low','high','close','volume'
			"""
			comb_index = None # datetime作为index，不同股票之间取并集，对数据做相应的填充
			for s in self.symbol_list:
				self.symbol_data[s] = pd.io.parsers.read_csv(
					                    os.path.join(self.csv_dir, %s.csv % s),
					                    header=0, index_col=0,
					                    names = ['datetime','open','low','high','close','volume']
					                    )
				if comb_index is None:
					comb_index = self.symbol_data[s].index
				else:
					comb_index.union(self.symbol_data[s].index) # 取datetime index的并集
					                                            # 因为不同股票的交易时间不同
                
                # 将字典中该只股票的最新数据设置为None，例如{'600008':[],}
                # 不用担心，在下面update_bars()方法中会更新出实际意义的数据
			    self.latest_symbol_data[s] = []


            # TODO: speed up for-loops! 必须要加速，不然太慢啦
			for s in self.symbol_list:
				# method指明对缺失值的填充方式，pad/ffill是用向前取值
				# 疑问1：
				#     是否应该做向后取值？这要看datetime是升序还是降序排列吧？!
				# 疑问2：
				#     iterrows()并不快！要想办法取代，itertuples() ？
				#     不过这里直接返回了iterrows生成器，可以惰性计算，格式（index, rows）
				self.symbol_data[s] = self.symbol_data[s].reindex(index=comb_index, method='pad').iterrows()

			def _get_new_bar(self, symbol):
				"""
				返回最新的bar，格式为(symbol, datetime, open, low, high, close, volume)
				生成器，每次调用生成一个新的bar，直到数据最后
				"""
				for b in self.symbol_data[symbol]:
					yield tuple([symbol, datetime.datetime.strptime(b[0], '%Y-%m-%d %H:%M:%S'),
						        b[1][0], b[1][1], b[1][3], b[1][4]])


			# 实现ABC CSVDataHandler中方法get_latest_bars()
			def get_latest_bars(self, symbol, N=1):
				"""
				从latest_symbol列表中返回最新的N个bar，或者所能返回的最大数量的bar
				"""
				try:
					bars_list = self.latest_symbol_data[symbol]
				except KeyError:
					print("数据库中不存在此股票！")
				else:
					return bars_list[-N:]

			# 实现ABC CSVDataHandler中方法get_latest_bars()
			def update_bars(self):
				"""
				对于symbol list中所有股票，将最新的bar更新到latest_symbol_data字典
				"""
				for s in self.symbol_list:
					try:
						bar = self._get_new_bar(s).next()
					except StopIteration:
						self.continue_backtest = False # 跳出回测while的flag
					else:
						if bar is not None:
							self.latest_symbol_data[s].append(bar)
				self.events.put(MarketEvent) # events是Queue结构

class TushareDataHandler(DataHandler):
	pass


class HDF5DataHandler(DataHandler):
	pass



if __name__ == "__main__":
    import queue

    events = queue.Queue()
    csv_dh = CSVDataHandler(events, os.path.join(os.getcwd(), 'datasources'), ['600008', '600018'])
    csv_dh.update_bars()
    print csv_dh.get_latest_bars('600008')



