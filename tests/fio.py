# -*- coding:utf-8 -*-
'''
  fio测试工具执行脚本
'''

import os,shutil,re,time,sys,copy
from test import BaseTest
from lpt.lib.error import *
from lpt.lib import lptxml
from lpt.lib import lptlog
from lpt.lib.share import utils
from lpt.lib import lptreport

class TestControl(BaseTest):
    '''
    继承BaseTest属性和方法
    '''
    def __init__(self, jobs_xml, job_node, tool, tarball='fio-2.1.10.tar.bz2'):
        super(TestControl, self).__init__(jobs_xml, job_node, tool, tarball)

    def setup(self):
        '''编译源码，设置程序
        '''
        if not self.check_bin(self.processBin):
            self.tar_src_dir = self.extract_bar()
            os.chdir(self.tar_src_dir)
            self.compile(configure_status=True, make_status=True)
            os.chdir(self.lpt_root)
        
    def run(self):
        tool_node = self.check_tool_result_node()
        self.config_file = os.path.join(self.tar_src_dir, self.get_config_value(tool_node, "config_file", "./fio-mixed.job", valueType=str))
        lptlog.info("使用配置文件: %s" % self.config_file)
        self.result_tmp_file = os.path.join(self.tmp_dir, "fio_output")
        self.filesize = self.get_config_value(tool_node, "filesize", "100M", valueType=str)
        lptlog.info("测试读写文件大小: %s" % self.filesize)
        f = open(self.config_file,'r')
        lines = f.read()
        f.close()
        f = open(self.config_file,'w')
        lines = re.sub('size=(\d+)M', 'size=%s'%self.filesize, lines)
        f.write(lines)
        f.close()
        self.mainParameters["parameters"] = "./fio --output %s %s"%(self.result_tmp_file, self.config_file)

        lptlog.info("----------开始测试")

        os.chdir(self.tar_src_dir)
        utils.system("./fio --output %s %s"%(self.result_tmp_file, self.config_file))

    def create_result(self):
        lptlog.info("----------创建结果")
     
        self.result_list = self.__match_index(self.result_tmp_file)

    def __match_index(self, file):

        if not os.path.isfile(file):
            return []

        lptlog.debug("在%s中搜索测试指标" % file)
        results_lines = utils.read_all_lines(file)

        labels = ('io', 'aggrb', 'minb', 'maxb', 'mint','maxt')
        parallel_template = {'parallels': '1,2,3,4', 'parallel': '1', 'iter': '1', 'times': '2'}        

        result_list = []
        count = 0
        for line in results_lines:
            if 'READ:' in line:
                tmp_list = []
                parallel_dict = copy.deepcopy(parallel_template)
                parallel_dict['parallel'] = str(count / 2 + 1)
                parallel_dict['iter'] = 'READ'
                tmp_list.append(parallel_dict)
                tmp_list.append(self.dict_generator(labels,line))
                result_list.append(tmp_list)
                count = count + 1
            elif 'WRITE:' in line:
                tmp_list = []
                parallel_dict = copy.deepcopy(parallel_template)
                parallel_dict['parallel'] = str(count / 2 + 1)
                parallel_dict['iter'] = 'WRITE'
                tmp_list.append(parallel_dict)
                tmp_list.append(self.dict_generator(labels,line))
                result_list.append(tmp_list)
                count = count + 1
                if count in [2,4,6,8]:
                    tmp_list = []
                    dict2 = result_list[-1][1]
                    dict1 = result_list[-2][1]
                    parallel_dict = copy.deepcopy(parallel_template)
                    parallel_dict['parallel'] = str(count / 2)
                    parallel_dict['iter'] = 'Average'
                    tmp_list.append(parallel_dict)
                    tmp_list.append(self.dict_average(dict1, dict2))
                    result_list.append(tmp_list)

        return result_list

    def dict_generator(self, labels, line):
        result_dict = {}
        line = line.replace(',','')
        line = line.split()
        for l,v in zip(labels, (line[1].split('=')[1][:-2], line[2].split('=')[1][:-4], line[3].split('=')[1][:-4], line[4].split('=')[1][:-4], line[5].split('=')[1][:-4], line[6].split('=')[1][:-4])):
            result_dict[l] = "%s" % v
        return result_dict

    def dict_average(self, dict1, dict2):
        result_dict = {}
        for k,v in dict1.items():
            try:
                result_dict[k] = str((float(dict1[k]) * 0.33 + float(dict2[k]) * 0.67))
            except e:
                raise e
                sys.exit()
        return result_dict

