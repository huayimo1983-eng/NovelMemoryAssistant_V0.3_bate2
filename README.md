# 小说项目管理系统 V0.3-beta

这是面向长篇/短篇自动写作流程的本地小说项目管理工具。

## 版本定位

V0.3-alpha 主要打通“导入—入库—设置当前有效版本—导出写作包”。

V0.3-beta 新增重点：

1. DOCX / TXT / MD 普通正文快速导入；
2. 阿拉伯数字和中文数字章节识别；
3. 当前卷、作者 IP、平台信息进入写作包；
4. 版本对比基础功能；
5. 大纲锁定区 / 防跑偏规则；
6. 人物状态卡；
7. 伏笔台账；
8. 风险灯；
9. 一键生成偏纲审查包；
10. 写作包自动带上大纲、人物、伏笔和风险提示。

## 运行

```bash
pip install -r requirements.txt
python app/main.py
```

## 打包 Windows EXE

```bat
build_exe.bat
```

GitHub Actions 也已包含 Windows 打包 workflow。

## 数据位置

默认数据库和导出文件保存在：

```text
C:\Users\你的用户名\.novel_memory_assistant_v03_beta
```

## 注意

这是 beta 初版，已有防跑偏与版本对比框架，但智能文学审稿仍需要通过“偏纲审查包”交给 ChatGPT 完成。


## 打包修正说明

PyInstaller 打包命令已加入 `--paths . --collect-submodules app`，用于确保 app.services、app.db、app.core、app.ui 等模块全部打入 exe。
