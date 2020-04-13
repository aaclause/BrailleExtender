# coding: utf-8
# brailleTablesHelper.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2020 André-Abush CLAUSE, released under GPL.
import addonHandler
import brailleTables
import config
from typing import Optional, List, Tuple
from logHandler import log

addonHandler.initTranslation()

listContractedTables = lambda tables=None: [table for table in (tables or brailleTables.listTables()) if table.contracted]
listUncontractedTables = lambda tables=None: [table for table in (tables or brailleTables.listTables()) if not table.contracted]
listInputTables = lambda tables=None: [table for table in (tables or brailleTables.listTables()) if table.input]
listOutputTables = lambda tables=None: [table for table in (tables or brailleTables.listTables()) if table.output]
listTablesFileName = lambda tables=None: [table.fileName for table in (tables or brailleTables.listTables())]
listTablesDisplayName = lambda tables=None: [table.displayName for table in (tables or brailleTables.listTables())]

def fileName2displayName(l):
	allTablesFileName = listTablesFileName()
	o = []
	for e in l:
		if e in allTablesFileName: o.append(allTablesFileName.index(e))
	return ', '.join([brailleTables.listTables()[e].displayName for e in o])

def getPreferedTables() -> Tuple[List[str]]:
	allInputTablesFileName = listTablesFileName(listInputTables())
	allOutputTablesFileName = listTablesFileName(listOutputTables())
	preferedInputTablesFileName = config.conf["brailleExtender"]["preferedInputTables"].split('|')
	preferedOutputTablesFileName = config.conf["brailleExtender"]["preferedOutputTables"].split('|')
	inputTables = [fn for fn in preferedInputTablesFileName if fn in allInputTablesFileName]
	outputTables = [fn for fn in preferedOutputTablesFileName if fn in allOutputTablesFileName]
	return inputTables, outputTables

def getPreferedTablesIndexes() -> List[int]:
	preferedInputTables, preferedOutputTables = getPreferedTables()
	tablesFileName = [table.fileName for table in brailleTables.listTables()]
	o = []
	for l in [preferedInputTables, preferedOutputTables]:
		o_ = []
		for i, e in enumerate(l):
			if e in tablesFileName: o_.append(tablesFileName.index(e))
		o.append(o_)
	return o

def getPostTables() -> List[str]:
	tablesFileName = [table.fileName for table in brailleTables.listTables()]
	l = config.conf["brailleExtender"]["postTables"].split('|')
	return [fn for fn in l if fn in tablesFileName]

def getPostTablesIndexes() -> List[int]:
	postTablesFileName = getPostTables()
	tablesFileName = [table.fileName for table in brailleTables.listTables()]
	o = []
	for i, e in enumerate(postTablesFileName):
		if e in tablesFileName: o.append(tablesFileName.index(e))
	return o

def cleanTablesFileName(tables: List[str], output: Optional[bool]=False) -> List[str]:
	listTablesFileName = listTablesFileName()
	for t in tables:
		if not t in listTablesFileName: tables.remove(l)
	return tables

def getCustomBrailleTables():
	return [config.conf["brailleExtender"]["brailleTables"][k].split('|', 3) for k in config.conf["brailleExtender"]["brailleTables"]]

def isContractedTable(fileName):
	listContractedTables = listContractedTables()
	if fileName in tablesFN: return False
	return brailleTables.listTables()[tablesFN.index(fileName)].contracted

def getTablesFilenameByID(l: List[int]) -> List[int]:
	listTablesFileName = [table.fileName for table in brailleTables.listTables()]
	o = []
	size = len(listTablesFileName)
	for i in l:
		if i < size: o.append(listTablesFileName[i])
	return o

def translateUsableIn(s):
	if s.startswith('i:'): return _("input")
	elif s.startswith('o:'): return _("output")
	elif s.startswith('io:'): return _("input and output")
	else: return _("None")