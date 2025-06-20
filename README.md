### 数据库版本
    (PostgreSQL) 9.4

### 启动本地开发环境前准备：
    0、安装 python 3.6.8版本
    1. 创建虚拟环境
        在本地创建一个专门存放虚拟环境的目录，如：mkdir ~/.virtualenvs
        进入到虚拟环境目录：cd ~/.virtualenvs
        为项目创建虚拟环境：python3.6 -m venv project-farm-env
        进入虚拟环境：source project-farm-env/bin/activate
        回到项目目录下安装依赖：pip install -r requirements.txt 
    2. 将项目目录下secret.py文件，复制到gearfarm目录下，并设置相关配置项(项目目录下secret.py只是模板,尽量不要修改)
    3. 安装redis 可设置为开机自启

### 启动本地开发环境
    进入项目目录下(先创建python环境)
    1. 启动python环境：source ~/.virtualenvs/project-farm-env/bin/activate
    2. export DJANGO_SETTINGS_MODULE=gearfarm.my_settings.development_settings  指定项目的配置
       若有新的migrations文件 先migrate：python manage.py migrate
    3. python manage.py runserver
    创建第一个用户：
    1、首次使用可创建一个superuser: python manage.py createsuperuser
            后台的admin: http://127.0.0.1:8000/admin
            设置用户的手机号后  在前端用 手机号+测试验证码（666888）登录
            
    其他脚本：
    #创建权限
    python manage.py rebuild_permissions_from_init_data
    #从正式环境同步权限
    python manage.py sync_permissions_groups_from_production_env
    其他（可忽略）：
        有一部分功能比如报告编辑器目前还集成在后端中，启动前端部分server
        npm install --registry=https://registry.npm.taobao.org
        npm run dev

### 启动celery 定时异步任务
    本地启动celery work:
        export DJANGO_SETTINGS_MODULE=gearfarm.my_settings.development_settings
        celery worker -A gearfarm --loglevel=INFO
    本地启动celery任务调度器 把定时任务按时添加到任务队列:
        export DJANGO_SETTINGS_MODULE=gearfarm.my_settings.development_settings
        celery beat -A gearfarm --loglevel=INFO


### 其他配置文件说明
    gearfarm/secret.py是账户密码配置
    
    farm.conf是supervisor中gunicorn的配置文件
    celery.conf是supervisor中celery的配置文件，
    
    secret.py中PHANTOMJS_PATH为phantomjs路径 根据自己系统下载后，配置一下路径
    下载地址http://phantomjs.org/download.html

### 服务器上执行脚本示例:
    cd /home/deployer/farm/current
    source /home/deployer/farm/venv/bin/activate
    export DJANGO_SETTINGS_MODULE=gearfarm.my_settings.production_settings
    python manage.py update_existing_playbook

### 报告生成PDF依赖工具
    1、Prince-11.4 下载地址https://www.princexml.com/download/11/
    2、GhostScript 7.07.1 下载地址https://ghostscript.en.softonic.com/


### 前端部分代码的说明:
    1. 说明：
        路由配置在后端python代码中，每个路由指向一个html(html在每个应用目录的templates中)
        每个html页面除了继承主模板外 可能会有自己单独的js css文件
        前端组件定义在farmbase/static/components中
    2、静态资源路径
        静态资源在每个应用目录下static中，一般会命名三个目录images、style、scripts分别存放图片、css、js
        html中引用scss可以使用如下模板语言会自动编译成css、本地测试配置输出在在项目目录下的.cache/static/中：
        {% load sass_tags %}
        <link rel="stylesheet" href="{% sass_src 'reports/styles/report-mindmap.scss' %}" type="text/css">
    3、js的编译
        编译工具使用的webpack 配置文件 webpack.config.js
        可编译js的入口在每个应用目录下static中的entry中 如：projects/static/projects/scripts/entry
        编译后js的出口在项目目录下的 static/output中  打包前后js会保持同名
        编译的准备：
            安装npm、安装包npm install --registry=https://registry.npm.taobao.org
            本地开发时 本地可以启动一个实时编译js的服务
            npm run dev
            可通过如下方式引用
            <!--<script src="http://localhost:8099/common.bundle.js"></script>-->
            <!--<script src="http://localhost:8099/project_create_project.js"></script>-->
         本地开发结束后，上线前修改js的引用路径如下：
            <script src="{% static 'farm_output/common.bundle.js' %}"></script>
            <script src="{% static 'farm_output/project_create_project.js' %}"></script>
         现在的引用方式 前缀通过一个配置项JS_BUILD_OUTPUT_PATH：
         <script src="{{js_build_output_path}}}/common.bundle.js"></script>
         <script src="{{js_build_output_path}}/project_position_needs.js"></script>