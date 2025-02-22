import asyncio
import os
import random
import string
import time

import requests

from libs.base import BaseClient

name_map = {
    '项目管理': [['week_new_project', 0]],
    '代码托管': [['week_new_git', 0], ['open_code_task', 1], ['push_code_task', 2]],
    'CloudIDE': [['open_ide_task', 0]],
    '代码检查': [['week_new_code_check', 0], ['check_code_task', 1]],
    '编译构建': [['week_new_compile_build', 0], ['compile_build_task', 1]],
    '部署': [['deploy_task', 1]],
    '发布': [['upload_task', 0]],
    '流水线': [['week_new_pipeline', 0], ['pipeline_task', 1]],
    '接口测试': [['week_new_api_test_task', 0], ['api_test_task', 1]],
    '测试管理': [['new_test_task', 0]],
    'APIG网关': [['new_new_api_task', 0], ['run_api_task', 1]],
    '函数工作流': [['new_fun_task', 0]],
    '使用API  Explorer完在线调试': 'api_explorer_task',
    '使用API Explorer在线调试': 'api2_explorer_task',
    '使用Devstar生成代码工程': 'dev_star_task',
    '浏览Codelabs代码示例': 'view_code_task',
    '体验DevStar快速生成代码': 'fast_dev_star',
}

init_name_map = {
    # '项目管理': [['week_new_project', 0]],
    # '代码托管': [['week_new_git', 0]],
    # '代码检查': [['week_new_code_check', 0]],
    # '编译构建': [['week_new_compile_build', 0]],
    # '部署': [['week_new_deploy', 0]],
    # '流水线': [['week_new_pipeline', 0]],
    '使用API  Explorer完在线调试': 'api_explorer_task',
    '使用API Explorer在线调试': 'api_explorer_task',
    # '使用Devstar生成代码工程': 'dev_star_task',
}


class BaseHuaWei(BaseClient):

    def __init__(self):
        super().__init__()
        self.url = 'https://devcloud.huaweicloud.com/bonususer/home/makebonus'
        self.task_page = None
        self.create_done = True
        self.home_url = None
        self.cancel = False

    async def after_handler(self, **kwargs):
        credit = kwargs.get('result')
        username = kwargs.get('username')
        if credit:
            self.logger.warning(f"{username} -> {credit}\n")
            if type(credit) == str:
                credit = int(credit.replace('码豆', '').strip())

            _id = f'{self.parent_user}_{username}' if self.parent_user else self.username
            requests.post(f'{self.api}/huawei/save', {'name': _id, 'credit': credit})

    async def start(self):
        if self.page.url != self.url:
            await self.page.goto(self.url, {'waitUntil': 'load'})

        id_list = ['experience-missions', 'middleware-missions']
        for _id in id_list:
            try:
                await self.execute(_id, 'ul.devui-nav li.ng-star-inserted', '', True, name_map)
            except Exception as e:
                self.logger.debug(e)

        try:
            await self.regular()
        except Exception as e:
            self.logger.debug(e)

        try:
            await self.init_account()
        except Exception as e:
            self.logger.debug(e)

    async def regular(self):
        await self.execute('regular-missions', '.daily-list li', 'feedback-', False, name_map)

    async def init_account(self):
        # await self.execute('experience-missions', 'ul.devui-nav li.ng-star-inserted', '', True, init_name_map)

        await self.page.goto('https://devcloud.huaweicloud.com/bonususer/home/new', {'waitUntil': 'load'})
        await asyncio.sleep(2)
        await self.execute('new-tasks-box', 'li.hot-task-item', 'new-task', False, init_name_map)

    async def execute(self, element_id, element_list_name, task_node, is_tab=True, task_map=None):
        elements = await self.page.querySelectorAll(f'#{element_id} {element_list_name}')
        for i, element in enumerate(elements):
            if self.cancel:
                break

            if is_tab:
                name = str(await element.Jeval('a', 'el => el.textContent')).strip()
                task_list = task_map.get(name)
                if task_list is None:
                    continue

                for task in task_list:
                    await element.click()
                    await asyncio.sleep(1)
                    task_node = f'#{element_id} #{element_id}-{task[1]}'
                    await self.run_task(task_node, task[0])
            else:
                _task_node = f'#{element_id} #{task_node}{i}'
                task_name = str(await self.page.Jeval(f'{_task_node} h5', 'el => el.textContent')).strip()
                if not task_map.get(task_name):
                    continue

                await self.run_task(_task_node, task_map.get(task_name))

    async def is_done(self, node, task_fun):
        try:
            is_done = await self.page.querySelector(f"{node} .complate-img")
            if is_done:
                if self.create_done and 'week' in task_fun:
                    return False
                return True
            is_done = await self.page.querySelector(f"{node} img.completed")
            if is_done:
                if self.create_done and 'week' in task_fun:
                    return False
                return True
        except Exception as e:
            self.logger.debug(e)
        return False

    async def run_task(self, task_node, task_fun):
        task_name = await self.page.Jeval(f'{task_node} h5', 'el => el.textContent')

        if await self.is_done(task_node, task_fun):
            self.logger.warning(f'{task_name} -> DONE.')
            return True

        await self.page.click(task_node)
        await asyncio.sleep(2)
        self.logger.info(f'{task_name}')

        try:
            self.task_page = await self.get_new_page()
            await self.task_page.setUserAgent(self.ua)
        except Exception as e:
            self.logger.error(e)
            raise e

        try:
            func = getattr(self, task_fun)
            # await func()
            await asyncio.wait_for(func(), timeout=100.0)
            self.logger.warning(f'{task_name} -> DONE.')
        except asyncio.TimeoutError as t:
            self.logger.debug(t)
            # await self.send_photo(self.task_page, task_fun)
        except Exception as e:
            self.logger.error(e)
        finally:
            await self.close_page()
            await asyncio.sleep(2)
            return True

    async def get_credit(self):
        for i in range(3):
            if self.page.url != self.url:
                await self.page.goto(self.url, {'waitUntil': 'load'})
            else:
                await self.page.reload({'waitUntil': 'load'})
            await asyncio.sleep(5)
            try:
                return str(await self.page.Jeval('#homeheader-coins', 'el => el.textContent')).replace('码豆', '').strip()
            except Exception as e:
                self.logger.debug(e)
        return 0

    async def print_credit(self, user_name):
        new_credit = await self.get_credit()
        self.logger.info(f'码豆: {new_credit}')
        message = f'{user_name} -> {new_credit}'
        self.dingding_bot(message, '华为云码豆')

    async def sign_task(self):
        try:
            await asyncio.sleep(5)
            info = await self.page.Jeval(
                '#homeheader-signin span.button-content, #homeheader-signined  span.button-content',
                'el => el.textContent')
            sign_txt = str(info).strip()
            self.logger.info(sign_txt)
            if sign_txt.find('已签到') == -1:
                await self.page.click('#homeheader-signin')
                await asyncio.sleep(3)
        except Exception as e:
            self.logger.warning(e)

    async def get_new_page(self):
        await asyncio.sleep(2)
        await self.page.click('.modal.in .modal-footer .devui-btn')
        await asyncio.sleep(5)
        page_list = await self.browser.pages()
        await page_list[-1].setViewport({'width': self.width, 'height': self.height})
        return page_list[-1]

    async def close_page(self):
        page_list = await self.browser.pages()
        if len(page_list) > 1:
            page = page_list[-1]
            if page.url != self.url:
                await page.close()

    async def api_explorer_task(self):
        await asyncio.sleep(3)
        html = str(await self.task_page.JJeval('.userInfo', '(els) => els.map(el => el.outerHTML)'))
        if html.find('English') != -1:
            items = await self.task_page.querySelectorAll('.userInfo')
            await items[1].hover()
            await asyncio.sleep(2)
            await self.task_page.click('.cdk-overlay-container .dropdown-item')
            await asyncio.sleep(5)

        await self.task_page.click('#debug')
        await asyncio.sleep(3)

    async def api2_explorer_task(self):
        _url = 'https://apiexplorer.developer.huaweicloud.com/apiexplorer/doc?product=DevStar&api=ListPublishedTemplates'
        await self.task_page.goto(_url, {'waitUntil': 'load'})
        await self.api_explorer_task()

    async def dev_star_task(self):
        await asyncio.sleep(2)
        await self.task_page.waitForSelector('#confirm-download-btn', {'visible': True})
        await self.task_page.click('.template-dynamic-paramter-title .devui-btn')
        await asyncio.sleep(2)
        await self.task_page.click('#confirm-upload-btn')
        await asyncio.sleep(3)

    async def view_code_task(self):
        await asyncio.sleep(10)
        await self.task_page.click('#code-template-cards .card-width:nth-child(2) .code-template-card-title')
        await asyncio.sleep(2)

    async def open_code_task(self):
        await asyncio.sleep(5)
        items = await self.task_page.querySelectorAll('div.devui-table-view tbody tr')
        if items and len(items):
            await self.task_page.evaluate(
                '''() =>{ document.querySelector('div.devui-table-view tbody tr:nth-child(1) td:nth-child(8) i.icon-more-operate').click(); }''')
            await asyncio.sleep(1)
            await self.task_page.evaluate(
                '''() =>{ document.querySelector('ul.dropdown-menu li:nth-child(5) .devui-btn').click(); }''')
            await asyncio.sleep(20)

    async def open_ide_task(self):
        await asyncio.sleep(5)
        try:
            await self.task_page.click('.region-modal-button-content .region-modal-button-common')
            await asyncio.sleep(1)
        except Exception as e:
            self.logger.debug(e)

        await asyncio.sleep(3)
        await self.task_page.click(
            '.trial-stack-info .trial-stack:nth-child(1) .stack-content .stack-position .devui-btn')
        await asyncio.sleep(10)

    async def push_code_task(self):
        if self.git:
            now_time = time.strftime('%Y-%m-%d %H:%M:%S')
            cmd = [
                'cd /tmp',
                'git config --global user.name "caoyufei" && git config --global user.email "atcaoyufei@gmail.com"',
                f'git clone {self.git}',
                'cd /tmp/crawler',
                f'echo "{now_time}" >> time.txt',
                "git add .",
                "git commit -am 'time'",
                "git push origin master",
            ]
            os.system(' && '.join(cmd))
            os.system('rm -rf /tmp/crawler')
            await asyncio.sleep(1)

    async def week_new_compile_build(self):
        await asyncio.sleep(2)
        await self.task_page.waitForSelector('.devui-layout-main-content', {'visible': True})
        await self.task_page.click('.devui-layout-main-content #create_new_task')
        await asyncio.sleep(1)
        await self.task_page.click('.button-group .devui-btn-stress')
        await asyncio.sleep(5)
        template = await self.task_page.querySelectorAll('.template-content li.template-item')
        await template[3].click()
        await asyncio.sleep(1)
        await self.task_page.click('.button-group .devui-btn-stress')

        await asyncio.sleep(5)
        card_list = await self.task_page.querySelectorAll('.task-detail-cardlist .card-li')
        await card_list[2].hover()
        await asyncio.sleep(1)
        await self.task_page.click('.task-detail-cardlist .card-li:nth-child(3) .add-btn')
        await asyncio.sleep(2)
        await self.task_page.click('.button-group .devui-btn-stress')
        await asyncio.sleep(2)

    async def compile_build_task(self):
        await asyncio.sleep(1)
        node = 'div.devui-table-view tbody tr:nth-child(1) .operation-btn-section .devui-btn:nth-child(1)'
        await self.task_page.evaluate('''() =>{ document.querySelector('%s').click(); }''' % node)
        await asyncio.sleep(1)

        node = 'ul.devui-dropdown-menu li:nth-child(1) a'
        await self.task_page.evaluate('''() =>{ document.querySelector('%s').click(); }''' % node)
        await asyncio.sleep(2)
        await self.task_page.click('.modal-footer .devui-btn-primary')
        await asyncio.sleep(8)

    async def check_code_task(self):
        await asyncio.sleep(5)
        task_list = await self.task_page.querySelectorAll('.devui-table tbody tr')
        task_id = await task_list[0].Jeval('.task-card-name span', "el => el.getAttribute('id')")
        task_id = task_id.replace('task_name', 'task_execute')
        if await self.task_page.querySelector(f'#{task_id}'):
            await self.task_page.click(f'#{task_id}')
        else:
            btn_list = await self.task_page.querySelectorAll('.devui-btn-text-dark')
            await btn_list[0].click()
            await asyncio.sleep(1)
            await self.task_page.click(f'#{task_id}')
        await asyncio.sleep(5)

    async def week_new_deploy(self):
        await asyncio.sleep(2)
        await self.task_page.waitForSelector('.devui-layout-operate', {'visible': True})
        await self.task_page.click('.devui-layout-operate #taskCreate')
        await asyncio.sleep(1)
        await self.task_page.click('.step-group .devui-btn-stress')
        await asyncio.sleep(5)

        template_list = await self.task_page.querySelectorAll('.template-list .template-item')
        await template_list[1].click()
        await asyncio.sleep(0.5)
        await self.task_page.click('.step-group .devui-btn-stress')
        await asyncio.sleep(3)
        items = await self.task_page.querySelectorAll('.category-wrapper ul.devui-nav li')
        await items[4].click()
        await asyncio.sleep(3)

        card_list = await self.task_page.querySelectorAll('.task-detail-cardlist .card-li')
        await card_list[0].hover()
        await asyncio.sleep(0.5)
        await self.task_page.click('.task-detail-cardlist .card-li:nth-child(1) .add-btn')
        await asyncio.sleep(1)

        link_list = await self.task_page.querySelectorAll('.marked-text .devui-link')
        await link_list[1].click()

        await asyncio.sleep(10)
        page_list = await self.browser.pages()
        await page_list[-1].setViewport({'width': self.width, 'height': self.height})
        new_page = page_list[-1]
        await asyncio.sleep(2)
        await new_page.type('input.input-textarea-cn', self.username)
        await asyncio.sleep(0.5)
        await new_page.click('.btn-box .devui-btn-stress')
        await asyncio.sleep(2)
        await new_page.close()

        await self.task_page.click('#DeploymentGroup_groupId_button')
        await asyncio.sleep(2)
        await self.task_page.click('.deployment-select')
        await asyncio.sleep(0.5)
        await self.task_page.click('.devui-dropdown-item:nth-child(1)')
        await asyncio.sleep(0.5)
        await self.task_page.type('div#SingleLineText_port_to_stop input', ''.join(random.choices(string.digits, k=4)))
        await asyncio.sleep(0.5)
        await self.task_page.click('.deployman-create-content__button-group .devui-btn-primary')
        await asyncio.sleep(3)

    async def deploy_task(self):
        await asyncio.sleep(3)
        await self.task_page.click('#rf-task-execute')
        await asyncio.sleep(3)

    async def run_test(self):
        await self._close_test()
        await self.task_page.waitForSelector('div.devui-table-view', {'visible': True})
        # string = await self.task_page.Jeval('div.devui-table-view tbody tr:nth-child(1) td:nth-child(12)',
        #                                     'el => el.outerHTML')
        # print(string)

        await self.task_page.evaluate(
            '''() =>{ document.querySelector('div.devui-table-view tbody tr:nth-child(1) td:nth-child(12) i.icon-run').click(); }''')

        await asyncio.sleep(5)

    async def api_test_task(self):
        await asyncio.sleep(2)
        await self._close_test()
        await self._tab_api_test()
        await self.task_page.evaluate(
            '''() =>{ document.querySelector('div.devui-table-view tbody tr:nth-child(1) i.icon-run').click(); }''')
        await asyncio.sleep(5)

    async def week_new_pipeline(self):
        await asyncio.sleep(2)
        await self.task_page.click('#createPipeline')
        await asyncio.sleep(1)
        await self.task_page.click('.content .devui-dropup')
        await asyncio.sleep(0.5)
        await self.task_page.click('.devui-dropdown-item:nth-child(1)')
        await asyncio.sleep(0.5)
        await self.task_page.click('.pipeline-edit-tab .devui-btn-primary')
        await asyncio.sleep(0.5)

        dropdowns = await self.task_page.querySelectorAll('.devui-dropup')
        for dropdown in dropdowns:
            await dropdown.click()
            await asyncio.sleep(1)
            dropdown_item = await dropdown.querySelectorAll('.devui-dropdown-item')
            await dropdown_item[0].click()
            await asyncio.sleep(0.5)

        await self.task_page.click('.pipeline-edit-tab .devui-btn-primary')
        await asyncio.sleep(1)
        await self.task_page.click('.pipeline-edit-tab .devui-btn-primary')
        await asyncio.sleep(5)

    async def pipeline_task(self):
        await asyncio.sleep(1)
        await self.task_page.evaluate(
            '''() =>{ document.querySelector('div.devui-table-view tbody tr:nth-child(1) .icon-run').click(); }''')
        await asyncio.sleep(1)
        await self.task_page.click('.modal.in .devui-btn-primary')
        await asyncio.sleep(1)
        await self.task_page.click('.modal.in .devui-btn-primary')
        await asyncio.sleep(1)

        # dropdowns = await self.task_page.querySelectorAll('div.source-value')
        # dropup = await dropdowns[0].querySelectorAll('.devui-dropup')
        # await dropup[1].click()
        # await asyncio.sleep(2)
        # dropdown_item = await dropup[1].querySelectorAll('.devui-dropdown-item')
        # await dropdown_item[0].click()
        # await asyncio.sleep(0.5)
        # await self.task_page.click('.modal.in .devui-btn-primary')
        await asyncio.sleep(5)

    async def week_new_project(self):
        await asyncio.sleep(5)
        try:
            notice = await self.task_page.querySelector('#declaration-notice')
            if notice:
                btn_list = await self.task_page.querySelectorAll('.quick-create-phoenix .devui-btn')
                await btn_list[1].click()
                await asyncio.sleep(1)
                await self.task_page.click('#declaration-notice div.devui-checkbox label')
                await asyncio.sleep(1)
                await self.task_page.click('#declaration-notice .devui-btn.devui-btn-primary')
                await asyncio.sleep(1)
        except Exception as e:
            self.logger.debug(e)

        try:
            btn_list = await self.task_page.querySelectorAll('.quick-create-phoenix .devui-btn')
            await btn_list[0].click()
            await asyncio.sleep(2)
        except Exception as e:
            await self.send_photo(self.task_page, 'week_new_project')
            self.logger.exception(e)
            await self.close()
            self.cancel = True

    async def week_new_git(self):
        await asyncio.sleep(5)
        no_data = await self.task_page.querySelector('.new-list .no-data')
        await self.task_page.waitForSelector('.pull-right', {'visible': True})
        await self.task_page.click('.pull-right .devui-btn-primary')
        await asyncio.sleep(1)
        git_name = ''.join(random.choices(string.ascii_letters, k=6))
        if not no_data:
            git_name = 'crawler'
        await self.task_page.type('#rname', git_name)
        await asyncio.sleep(0.5)

        btn_list = await self.task_page.querySelectorAll('.new-repo-row-center:nth-child(1) .devui-checkbox')
        await btn_list[2].click()

        await self.task_page.click('#newAddRepoBtn')
        await asyncio.sleep(8)

        git_list = await self.task_page.querySelectorAll('.devui-table tbody tr')
        if git_list and len(git_list) and git_name == 'crawler':
            await self.task_page.click('#repoNamecrawler')
            await asyncio.sleep(10)
            git_url = await self.task_page.Jeval('.clone-url input', "el => el.getAttribute('title')")
            _user = self.parent_user if self.parent_user else self.username
            git_url = git_url.replace('git@', f'https://{_user}%2F{self.username}:{self.password}@')
            self.git = git_url.replace('com:', 'com/')
            self.logger.info(self.git)

    async def week_new_code_check(self):
        await self.task_page.waitForSelector('.pull-right', {'visible': True})
        await self.task_page.click('.pull-right .devui-btn-primary')
        await asyncio.sleep(8)
        btn = await self.task_page.querySelector('#codecheck-new-task-btn-0')
        if btn:
            await btn.click()
            await asyncio.sleep(1)
            await self.task_page.click('.btn-wrap .devui-btn-primary')
            await asyncio.sleep(5)

    async def upload_task(self):
        await asyncio.sleep(3)
        # items = await self.task_page.querySelectorAll('')

        await self.task_page.click('#releasemanUploadDrop tbody tr:nth-child(1) td a.column-link')
        await asyncio.sleep(3)
        await self.task_page.waitForSelector('#upload_file', {'visible': True})
        f = await self.task_page.querySelector('#releaseman-file-select')
        await f.uploadFile(__file__)
        await asyncio.sleep(3)

    async def new_test_task(self):
        await asyncio.sleep(2)
        await self.task_page.click('#global-guidelines .icon-close')
        await asyncio.sleep(1)
        await self.task_page.click('.guide-container .icon-close')
        await asyncio.sleep(1)
        await self.task_page.waitForSelector('div.create-case', {'visible': True})
        await self.task_page.click('div.create-case')
        await asyncio.sleep(5)
        await self.task_page.type('#caseName', ''.join(random.choices(string.ascii_letters, k=6)))
        await self.task_page.click('div.footer .devui-btn-stress')
        await asyncio.sleep(5)

    async def week_new_api_test_task(self):
        await asyncio.sleep(2)
        await self._close_test()
        await self._tab_api_test()
        await self.task_page.waitForSelector('div.create-case', {'visible': True})
        await self.task_page.click('div.create-case')
        await asyncio.sleep(2)
        await self.task_page.type('#caseName', ''.join(random.choices(string.ascii_letters, k=6)))
        await self.task_page.click('div.footer .devui-btn-stress')
        await asyncio.sleep(3)

    async def new_new_api_task(self):
        await asyncio.sleep(15)
        self.logger.debug(self.task_page.url)

    async def run_api_task(self):
        await asyncio.sleep(3)
        await self.task_page.click('div.ti-intro-modal .ti-btn-danger')
        await asyncio.sleep(3)
        await self.task_page.click('#send')
        await asyncio.sleep(2)
        await self.task_page.click('.pull-left .cti-button')
        await asyncio.sleep(5)
        await self.task_page.click('.pull-right.mr10.cti-button')
        await asyncio.sleep(5)
        await self.task_page.click('.ti-btn-danger.ml10.ng-binding')

    async def new_fun_task(self):
        url = self.task_page.url
        if url.find('serverless/dashboard') == -1:
            url = f'{url}#/serverless/dashboard'
            await self.task_page.goto(url, {'waitUntil': 'load'})

        await asyncio.sleep(2)
        try:
            await self.task_page.click('#rightWrap .ant-row .ant-btn')
            await asyncio.sleep(3)
            await self.task_page.type('#name', ''.join(random.choices(string.ascii_letters, k=6)), {'delay': 30})
            await asyncio.sleep(3)
            await self.task_page.click('.preview .ant-btn-primary')
            await asyncio.sleep(5)
        except Exception as e:
            self.logger.warning(e)
        finally:
            return

    async def fast_dev_star(self):
        await asyncio.sleep(5)
        await self.task_page.click('.code-template-codebase-right-operations-panel .devui-btn-common')
        # await asyncio.sleep(1)
        # await self.task_page.click('.operation-next')
        await asyncio.sleep(3)
        await self.task_page.click('#deploy-btn')

        await asyncio.sleep(15)


    async def delete_function(self):
        page = await self.browser.newPage()
        url_list = ['https://console.huaweicloud.com/functiongraph/?region=cn-north-4#/serverless/functionList',
                    'https://console.huaweicloud.com/functiongraph/?region=cn-south-1#/serverless/functionList']
        for _url in url_list:
            await page.goto(_url, {'waitUntil': 'load'})
            await page.setViewport({'width': self.width, 'height': self.height})
            await asyncio.sleep(5)
            elements = await page.querySelectorAll('td[style="white-space: normal;"]')
            for element in elements:
                a_list = await element.querySelectorAll('a.ti3-action-menu-item')
                # content = str(await (await element.getProperty('textContent')).jsonValue()).strip()
                if len(a_list) == 2:
                    try:
                        await a_list[1].click()
                        await asyncio.sleep(1)
                        await page.type('.modal-confirm-text input[type="text"]', 'DELETE')
                        await asyncio.sleep(1)
                        await page.click('.ti3-modal-footer .ti3-btn-danger')
                        await asyncio.sleep(1)
                    except Exception as e:
                        self.logger.exception(e)

        await page.close()
        await asyncio.sleep(1)

    async def check_project(self):
        page = await self.browser.newPage()
        domains = ['https://devcloud.huaweicloud.com', 'https://devcloud.cn-north-4.huaweicloud.com']
        try:
            for domain in domains:
                url = f'{domain}/projects/v2/project/list?sort=&search=&page_no=1&page_size=40&project_type=&archive=1'
                res = await page.goto(url, {'waitUntil': 'load'})
                data = await res.json()
                if data.get('error') or not data.get('result'):
                    await asyncio.sleep(1)
                    continue

                projects = data['result']['project_info_list']
                self.home_url = domain

                if len(projects) > 0:
                    self.create_done = False
                    break
                await asyncio.sleep(1)
        except Exception as e:
            self.logger.error(e)
        finally:
            await page.close()
            self.logger.info(self.create_done)

    async def delete_project(self):
        page = await self.browser.newPage()
        domains = ['https://devcloud.huaweicloud.com', 'https://devcloud.cn-north-4.huaweicloud.com']
        for i in range(3):
            try:
                for domain in domains:
                    url = f'{domain}/projects/v2/project/list?sort=&search=&page_no=1&page_size=40&project_type=&archive=1'
                    res = await page.goto(url, {'waitUntil': 'load'})
                    data = await res.json()
                    if data.get('error') or not data.get('result'):
                        continue

                    for item in data['result']['project_info_list']:
                        try:
                            self.logger.warning(f"delete project {item['name']}")
                            delete_url = f"{domain}/projects/project/{item['project_id']}/config/info"
                            await page.goto(delete_url, {'waitUntil': 'load'})
                            await asyncio.sleep(2)
                            btn_list = await page.querySelectorAll('.modal-footer .btn')
                            if len(btn_list) == 2:
                                await btn_list[1].click()
                                await asyncio.sleep(1)

                            await page.click('.form-container .margin-right-s .devui-btn:nth-child(1)')
                            await asyncio.sleep(2)
                            await page.type('#deleteProject .projectInput', item['name'])
                            await asyncio.sleep(0.5)
                            await page.click('.dialog-footer .devui-btn-primary')
                            await asyncio.sleep(1)
                        except Exception as e:
                            self.logger.error(e)
                break
            except Exception as e:
                self.logger.error(e)
                await asyncio.sleep(5)
        await page.close()

    async def delete_api(self):
        page = await self.browser.newPage()
        try:
            await page.goto('https://console.huaweicloud.com/apig/?region=cn-north-4#/apig/multiLogical/openapi/list',
                            {'waitUntil': 'load'})
            await page.setViewport({'width': self.width, 'height': self.height})
            await asyncio.sleep(10)
            elements = await page.querySelectorAll('#openapi_list tr')
            if len(elements) < 2:
                return

            # 下线
            await page.click('#openapi_list tr:nth-child(1) th:nth-child(1)')
            await asyncio.sleep(0.5)
            await page.click('.apiList-groups .cti-button:nth-child(3) .cti-btn-container')
            await asyncio.sleep(1)
            await page.click('.ti-modal-dialog .cti-button:nth-child(1) .cti-btn-container')
            await asyncio.sleep(2)

            # 删除
            await page.click('#openapi_list tr:nth-child(1) th:nth-child(1)')
            await asyncio.sleep(0.5)
            await page.click('.apiList-groups .cti-button:nth-child(4) .cti-btn-container')
            await asyncio.sleep(3)
            await page.type('#deleteContent-text', 'DELETE')
            await asyncio.sleep(0.5)
            await page.click('.ti-modal-dialog .cti-button:nth-child(1) .cti-btn-container')
            await asyncio.sleep(2)
        except Exception as e:
            self.logger.debug(e)
        finally:
            await page.close()

    async def delete_api_group(self):
        page = await self.browser.newPage()
        try:
            await page.goto('https://console.huaweicloud.com/apig/?region=cn-north-4#/apig/multiLogical/openapi/group',
                            {'waitUntil': 'load'})
            await page.setViewport({'width': self.width, 'height': self.height})
            await asyncio.sleep(8)
            elements = await page.querySelectorAll('#openapi_group tbody tr')
            if len(elements) < 1:
                return

            await page.click('#openapi_group tbody tr:nth-child(1) td:nth-child(1) a')
            await asyncio.sleep(2)
            await page.click('.cti-fl-right .cti-button:nth-child(4) .cti-btn-container')
            await asyncio.sleep(1)
            await page.type('#tiny-text', 'DELETE')
            await asyncio.sleep(0.5)
            await page.click('#delG')
            await asyncio.sleep(2)
        except Exception as e:
            self.logger.debug(e)
        finally:
            await page.close()

    async def _close_test(self):
        try:
            await asyncio.sleep(1)
            await self.task_page.click('#global-guidelines .icon-close')
            await asyncio.sleep(2)
            await self.task_page.click('.guide-container .icon-close')
            await asyncio.sleep(1)
        except Exception as e:
            self.logger.debug(e)

    async def _tab_api_test(self):
        await asyncio.sleep(1)
        await self.task_page.waitForSelector('#testtype_1')
        await self.task_page.click('#testtype_1')
        await asyncio.sleep(1)

    async def sign_post(self):
#         tid_list = [87703, 87513, 87948, 87424, 87445, 87587, 87972, 87972]
#         n = random.randint(1, 2)
#         for i in range(n):
#             tid = random.choice(tid_list)
#             await self.page.goto(f'https://bbs.huaweicloud.com/forum/thread-{tid}-1-1.html', {'waitUntil': 'load'})
#             await self.page.waitForSelector('#fastpostsubmit')
#             content = random.choice(
#                 ['666', '回帖送码豆', '论坛回帖送码豆喽'])
#             await self.page.evaluate(
#                 '''() =>{ ue.setContent('<p>%s</p>'); }''' % content)
#             await asyncio.sleep(1)
#             await self.page.click('#fastpostsubmit')
#             await asyncio.sleep(5)

    async def post_reply(self):
#         await self.page.goto('https://bbs.huaweicloud.com/forum/thread-89722-1-1.html', {'waitUntil': 'load'})
#         await self.page.waitForSelector('#fastpostsubmit')
#         content = '#2020年终盛典# 我很期待这次盛典，祝盛典圆满成功！顺利召开！'
#         await self.page.evaluate(
#             '''() =>{ ue.setContent('<p>%s</p>'); }''' % content)
#         await asyncio.sleep(1)
#         await self.page.click('#fastpostsubmit')
#         await asyncio.sleep(10)

#         await self.page.goto('https://bbs.huaweicloud.com/forum/thread-89742-1-1.html', {'waitUntil': 'load'})
#         await self.page.waitForSelector('#fastpostsubmit')
#         content = ' #我和华为云的这一年#这一年是我和华为云相识的第一年，知道了华为云有很多课程，大拿讲课，受益颇丰。'
#         await self.page.evaluate(
#             '''() =>{ ue.setContent('<p>%s</p>'); }''' % content)
#         await asyncio.sleep(1)
#         await self.page.click('#fastpostsubmit')
#         await asyncio.sleep(5)

        # await self.page.goto('https://bbs.huaweicloud.com/forum/thread-80376-1-1.html', {'waitUntil': 'load'})
        # await self.page.waitForSelector('#fastpostsubmit')
        # await self.page.evaluate('''() =>{ document.querySelector('#tabeditor-2').click(); }''')
        # await asyncio.sleep(1)
        # await self.page.click('#tabeditor-2')
        # content = random.choice(
        #     [
        #         '![1024](https://bbs-img-cbc-cn.obs.cn-north-1.myhuaweicloud.com/data/attachment/forum/202010/09/204951b8y0xls2nopvc6az.png)',
        #         '![1024](https://bbs-img-cbc-cn.obs.cn-north-1.myhuaweicloud.com/data/attachment/forum/202010/09/161504wwp2tknsrfkzytrm.png)',
        #         '![1024](https://bbs-img-cbc-cn.obs.cn-north-1.myhuaweicloud.com/data/attachment/forum/202010/09/173512tnrpfkysqadqtlee.png)',
        #         '![1024](https://bbs-img-cbc-cn.obs.cn-north-1.myhuaweicloud.com/data/attachment/forum/202010/09/162825q3widemjdlppcjb0.png)',
        #         '![1024](https://bbs-img-cbc-cn.obs.cn-north-1.myhuaweicloud.com/data/attachment/forum/202010/10/111533ab4neej10wtrbmm6.png)',
        #     ])
        # await self.page.type('.textarea', content, {'delay': 30})
        # # await self.page.evaluate('''() =>{ document.querySelector('.textarea').value = '%s'; }''' % content)
        # # await self.page.evaluate('''() =>{ document.querySelector('#mditorBox').value = '%s'; }''' % content)
        # await asyncio.sleep(1)
        # await self.page.click('#fastpostsubmit')
        # await asyncio.sleep(5)

    # HDC flag 读书签到 3月23日-4月20日，累计29天
    async def hdc_read(self):
#         await self.page.goto(os.environ.get('FLAGURL'), {'waitUntil': 'load'})
#         await self.page.waitForSelector('#fastpostsubmit')
#         await asyncio.sleep(1)
#         await self.page.click('#tabeditor-2')
#         content = random.choice(
#                 [
#                     '每天坚持打卡', 
#                     '实现flag，打卡mark', 
#                     '坚持继续打卡~~', 
#                     '打卡++1', 
#                     'flag达成', 
#                     '记录一下', 
#                     'mark今天的打卡', 
#                     '打卡，坚持不停',
#                     '继续打卡'
#                 ])
#         await self.page.type('.textarea', content, {'delay': 30})
#         await asyncio.sleep(1)
#         await self.page.click('#fastpostsubmit')
#         await asyncio.sleep(30)
    
    # 【DevRun华为云开发者沙龙】听说牛羊也有自己的“健康码”？观看直播专家为你解答，还能参与盖楼活动，每周好礼等你拿！5月20日、5月27日、6月3日
    async def hdc_floor(self):
#         await self.page.goto('https://bbs.huaweicloud.com/forum/thread-127534-1-1.html', {'waitUntil': 'load'})
#         await self.page.waitForSelector('#fastpostsubmit')
#         await asyncio.sleep(1)
#         await self.page.click('#tabeditor-2')
#         for i in range(1,7):
#             content = random.choice(
#             [
#                     '健康监测：通过对牲畜个体的进行24小时的定时监测，每4小时采集并上次到华为云IoT平台，当分析耳温波动异常时，及时进行预警通知监管人员确认。', 
#                     '活体资产数量监管：主要解决所监管的牲畜个体数量符合，并且是活的两个问题。在圈舍安装视频摄像头对圈舍实时监控，然后通过吉星海自研发AI算法在边缘计算设备对监控视频画面的牲畜进行实时个别识别，并且将识别结果定时上传至我们的平台。当平台分析结果出现数据骤减时，进行预警并通知监管人员进行确认处理。', 
#                     '牲畜分布：根据采集的牲畜数据信息，对牲畜进行定位，生成牲畜分布地图，方便监管方能非常直观的掌握牲畜的动态分布情况。'
#             ])
#             await self.page.type('.textarea', content, {'delay': 30})
#             await asyncio.sleep(1)
#             await self.page.click('#fastpostsubmit')
#             await asyncio.sleep(30)
        
#         await self.page.goto('https://bbs.huaweicloud.com/forum/thread-126731-1-1.html', {'waitUntil': 'load'})
#         await self.page.waitForSelector('#fastpostsubmit')
#         await asyncio.sleep(1)
#         await self.page.click('#tabeditor-2')
#         for i in range(1,7):
#             content = random.choice(
#                 [
#                         '1.物联网“IoT” 的英文全称是（Internet of Things）。',
#                         '2.在（华为云学院）可以获取华为云各领域的免费课程。',
#                         '3.华为物联网职业认证目前有两个级别，分别是（HCIA）和（HCIP）。',
#                         '4.发表（5）篇原创优质博客，可以申请成为云享专家。',
#                         '5.目前华为云IoT的云享专家发布合格博客，每篇可获得（150）码豆。',
#                         '6.活动码豆可以在（码豆会员中心）兑换华为云周边、电子产品等实物奖品。',
#                         '7.华为云IoT的设备接入平台IoTDA每月提供（100万）条免费消息数。',
#                         '8.在华为云IoT论坛发布技术求助帖，工作日期间一般（2）小时内会有专家解答。',
#                         '9.（IoT边缘(IoT Edge)）是边缘计算在物联网行业的应用，它在靠近物或数据源头的边缘侧，融合网络、计算、存储、应用核心能力的开放平台，就近提供计算和智能服务，满足行业在实时业务、应用智能、安全与隐私保护等方面的基本需求。',
#                         '10.（设备接入服务(IoTDA)）是华为云的物联网平台，提供海量设备连接上云、设备和云端双向消息通信、批量设备管理、远程控制和监控、OTA升级、设备联动规则等能力，并可将设备数据灵活流转到华为云其他服务，帮助物联网行业用户快速完成设备联网及行业应用集成。',
#                         '11.（设备发放服务(IoT Device Provisioning)）可以帮助您可以轻松管理跨多区域海量设备的发放工作，实现单点发放管理，设备全球上线的业务目的。',
#                         '12.（全球SIM联接(Global SIM Link)）提供无线蜂窝物联网流量和eSIM/vSIM按需选网，享受当地资费，为客户提供一点接入、全球可达的一站式流量管理服务。',
#                         '13.（华为云IoT数据分析服务）基于物联网资产模型，整合IoT数据集成、清洗、存储、分析、可视化，为IoT数据开发者提供一站式服务，降低开发门槛，缩短开发周期，快速实现IoT数据价值变现。',
#                         '14.（Huawei LiteOS）是华为针对物联网领域推出的轻量级物联网操作系统。',
#                         '15.（华为云IoT）是买家、卖家、系统集成商的桥梁和纽带，助力设备和应用集成，使能行业应用服务，实现物联网应用的低成本复制。',
#                 ])
#             await self.page.type('.textarea', content, {'delay': 30})
#             await asyncio.sleep(1)
#             await self.page.click('#fastpostsubmit')
#             await asyncio.sleep(30)
