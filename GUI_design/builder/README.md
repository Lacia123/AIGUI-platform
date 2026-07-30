# AIGUI Builder

可扩展的容器 / 组件拖拽设计器。参考 `../test1.html` 与 Domain / RL Builder 设计稿。

## 启动

```powershell
cd GUI_design\builder
python start_server.py
```

或：

```powershell
python GUI_design\builder\start_server.py
```

浏览器会自动打开 http://127.0.0.1:8000/  
组件预览：http://127.0.0.1:8000/preview.html  
（需用 HTTP 服务，不要直接双击 `index.html`）

## 目录

```
builder/
  index.html                 # 设计器入口
  preview.html               # 组件样式平铺预览
  css/                       # 样式分层
  js/
    main.js                  # 装配侧栏 / 画布 / 工具栏
    preview.js               # 预览页：按注册表渲染全部组件
    core/                    # 拖拽、选中、序列化、注册聚合
    render/                  # DOM 工厂与组件渲染
    data/                    # 示例布局
  registry/
    containers.js            # 【扩容器】只改这里
    components.js            # 【扩组件】改这里 + render/components.js
```

## 容器两类

| 类型 | 作用 |
|---|---|
| **布局容器** | 行 / 列 / 瀑布流，默认无壳，只负责排布 |
| **组件容器（预设）** | 四宫格、左右分栏、Domain 页式等，拖入即带内容槽 |

叶子内容仍从「组件库」拖入各槽位。
