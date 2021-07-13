# tablehelper.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2020 André-Abush CLAUSE, released under GPL.
from brailleTables import listTables
from typing import List

def get_tables(tables=None, contracted=None, output=None, input=None):
	if not tables:
		tables = listTables()
	if isinstance(contracted, bool):
		tables = filter(lambda e: e.contracted == contracted, tables)
	if isinstance(input, bool):
		tables = filter(lambda e: e.input == input, tables)
	if isinstance(output, bool):
		tables = filter(lambda e: e.output == output, tables)
	return list(tables)


def get_file_names(tables=None):
	if not tables:
		tables = listTables()
	return [table.fileName for table in tables]


def get_file_names_by_display_names(l):
	file_names = get_file_names()
	o = []
	for e in l:
		if e in file_names:
			o.append(file_names.index(e))
	return [listTables()[e].displayName for e in o]


def get_display_names(tables=None):
	if not tables:
		tables = listTables()
	return [table.displayName for table in tables]


def get_indexes(l, tables):
	if not tables:
		tables = listTables()
	tables = get_file_names(tables)
	return [tables.index(e) for e in l if e in tables]


def get_table_by_file_name(FileName, tables=None):
	if not tables:
		tables = listTables()
	for table in tables:
		if table.fileName == FileName:
			return table
	return None


def get_tables_file_name_by_id(l: List[int], tables=None) -> List[int]:
	file_names = get_file_names(tables or listTables())
	o = []
	size = len(file_names)
	for i in l:
		if i < size:
			o.append(file_names[i])
	return o
