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
    def __init__(self, jobs_xml, job_node, tool, tarball='netperf-2.6.0.tar.bz2'):
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
        self.result_tmp_file = os.path.join(self.tmp_dir, "netperf_output")
        self.time = self.get_config_value(tool_node, "time", "100", valueType=int)
        lptlog.info("单项测试时间: %s秒" % self.time)
        self.server_ip = self.get_config_value(tool_node, "server_ip", "127.0.0.1", valueType=str)
        lptlog.info("Server端地址为: %s" % self.server_ip)
        self.password = self.get_config_value(tool_node, "password", "root", valueType=str)
        lptlog.info("使用账户root密码%s登录Server端" % self.password)
        self.mainParameters["parameters"] = "./src/netperf -t TCP_STREAM -H %s -l %s &&"%(self.server_ip, self.time)
        self.mainParameters["parameters"] += "./src/netperf -t UDP_STREAM -H %s -l %s &&"%(self.server_ip, self.time)
        self.mainParameters["parameters"] += "./src/netperf -t TCP_RR -H %s -l %s &&"%(self.server_ip, self.time)
        self.mainParameters["parameters"] += "./src/netperf -t UDP_RR -H %s -l %s &&"%(self.server_ip, self.time)
        self.mainParameters["parameters"] += "./src/netperf -t TCP_CRR -H %s -l %s"%(self.server_ip, self.time)

        lptlog.info("----------开始测试")

        os.chdir(self.tar_src_dir)
        utils.system("rm %s -f"%self.result_tmp_file)
        utils.system('echo "StrictHostKeyChecking no" >> /etc/ssh/ssh_config')
        setup_server_cmd = "sshpass -p '%s' scp src/netserver root@%s:/root"%(self.password, self.server_ip)
        utils.system('rm /root/.ssh/known_hosts -f')
        utils.system('rm /root/netserver -f')
        utils.system(setup_server_cmd)
        lptlog.info("拷贝Netperf Server端到%s"%self.server_ip)
        utils.system("sshpass -p '%s' ssh -lroot %s '%s'"%(self.password, self.server_ip,'pkill -9 netserver || :'))
        utils.system("sshpass -p '%s' ssh -lroot %s '%s'"%(self.password, self.server_ip,'/root/netserver'))
        lptlog.info("启动Server端")
        for i in range(2):
            for test in ['TCP_STREAM','UDP_STREAM','TCP_RR','UDP_RR','TCP_CRR']:
                lptlog.info("开始%s测试%s"%(test,i))
                utils.system("./src/netperf -t %s -H %s -l %s >> %s"%(test, self.server_ip, self.time, self.result_tmp_file))

    def create_result(self):
        lptlog.info("----------创建结果")
     
        self.result_list = self.__match_index(self.result_tmp_file)

    def __match_index(self, file):

        if not os.path.isfile(file):
            return []

        lptlog.debug("在%s中搜索测试指标" % file)
        results_lines = utils.read_all_lines(file)

        result_list = []        

        labels = ('TCP_STREAM','UDP_STREAM', 'TCP_RR', 'UDP_RR', 'TCP_CRR')
        parallel_template = {'parallels': '1', 'parallel': '1', 'iter': '1', 'times': '2'}        

        result1 = (results_lines[6].split()[4],results_lines[13].split()[3],results_lines[21].split()[5],results_lines[29].split()[5],results_lines[37].split()[5])
        result2 = (results_lines[45].split()[4],results_lines[52].split()[3],results_lines[60].split()[5],results_lines[68].split()[5],results_lines[76].split()[5])
        tmp_list = []
        parallel_dict = copy.deepcopy(parallel_template)
        tmp_list.append(parallel_dict)
        tmp_list.append(self.dict_generator(labels,result1))
        result_list.append(tmp_list)
        tmp_list = []
        parallel_dict = copy.deepcopy(parallel_template)
        parallel_dict['iter'] = '2'
        tmp_list.append(parallel_dict)
        tmp_list.append(self.dict_generator(labels,result2))
        result_list.append(tmp_list)
        tmp_list = []
        parallel_dict = copy.deepcopy(parallel_template)
        parallel_dict['iter'] = 'Average'
        tmp_list.append(parallel_dict)
        tmp_list.append(self.dict_average(result_list[0][1],result_list[1][1]))
        result_list.append(tmp_list)
        return result_list

    def dict_generator(self, labels, result):
        result_dict = {}
        for l,v in zip(labels,result):
            result_dict[l] = "%s" % v
        return result_dict

    def dict_average(self, dict1, dict2):
        result_dict = {}
        for k,v in dict1.items():
            try:
                result_dict[k] = str((float(dict1[k]) * 0.5 + float(dict2[k]) * 0.5))
            except e:
                raise e
                sys.exit()
        return result_dict

